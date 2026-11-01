package com.kopanka;

import android.app.Activity;
import android.app.AlertDialog;
import android.os.Bundle;
import android.content.SharedPreferences;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.Path;
import android.graphics.RectF;
import android.view.MotionEvent;
import android.view.View;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;
import android.widget.FrameLayout;
import android.widget.HorizontalScrollView;
import android.graphics.Typeface;
import android.os.Handler;
import android.os.Looper;
import android.view.Gravity;
import java.util.Calendar;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

/** KOPANKA 1.3.1: fixed map scale, hero-centered camera, two-tap movement. */
public class MainActivity extends Activity {
    private static final int W=48,H=48,N=W*H, START=24*W+24;
    private final boolean[] seen=new boolean[N], roads=new boolean[N], claimed=new boolean[N], cleared=new boolean[N];
    private final int[] infrastructure=new int[N], infraLevel=new int[N]; // 0 none, 1 bridge, 2 tunnel
    private final long[] builtAt=new long[N];
    private int target=-1;
    private final List<Integer> planned=new ArrayList<>();
    private final Handler movementHandler=new Handler(Looper.getMainLooper());
    private boolean walking=false;
    private final int[] terrain=new int[N]; // 0 grass,1 forest,2 stone,3 ore,4 lake,5 hill
    private int hero=START, coins=0,wood=0,stone=0,iron=0,stage=1,vehicle=0,energy=18,deliveries=0;
    private long lastDay=0;
    // Logistics: settlement inventory is separate from hero cargo and deposits.
    private int cargoWood=0,cargoStone=0,cargoIron=0,carryUpgrade=0,cartLevel=0;
    private boolean garage=false,truck=false;
    private final int[] deposit=new int[N];
    private int cargoTotal(){return cargoWood+cargoStone+cargoIron;}
    private int capacity(){return truck?150:cartLevel==2?50:cartLevel==1?30:carryUpgrade==1?15:10;}
    private String cargoText(){return "Вантаж: "+cargoTotal()+"/"+capacity()+"\nДеревина: "+cargoWood+" · Камінь: "+cargoStone+" · Залізо: "+cargoIron;}
    private void unload(){
        if(hero!=START||cargoTotal()==0)return;
        wood+=cargoWood;stone+=cargoStone;iron+=cargoIron;
        int amount=cargoTotal();cargoWood=cargoStone=cargoIron=0;
        save();refresh();msg("Доставлено на склад: "+amount+" од.");
    }
    private void gather(int tile,int amount){
        if(energy<2){msg("Потрібно 2 одиниці часу");return;}
        energy-=2;deposit[tile]+=amount;save();refresh();
        msg("Видобуто "+amount+" од. На ділянці: "+deposit[tile]);
        showTile(tile);
    }
    private void loadCargo(int tile){
        int qty=Math.min(deposit[tile],capacity()-cargoTotal());
        if(qty<=0){msg("Немає вільного місця або ресурсів");return;}
        if(terrain[tile]==1)cargoWood+=qty;
        else if(terrain[tile]==2)cargoStone+=qty;
        else cargoIron+=qty;
        deposit[tile]-=qty;save();refresh();
        msg("Завантажено "+qty+" од. · "+cargoTotal()+"/"+capacity());
    }
    private void logisticsMenu(){
        String options="Герой: "+(carryUpgrade==0?"10":"15")+" од.\nТачка: "+(cartLevel==0?"немає":cartLevel==1?"30 од.":"50 од.")+"\nГараж: "+(garage?"побудовано":"немає")+"\nВантажівка: "+(truck?"150 од.":"немає")+"\n\nСклад: "+wood+" дерева, "+stone+" каменю, "+iron+" заліза, "+coins+" монет";
        new AlertDialog.Builder(this).setTitle("Майстерня та логістика").setMessage(options)
            .setItems(new String[]{"Посилити героя (10 дерева, 5 каменю)","Виготовити тачку (15 дерева, 5 заліза)","Покращити тачку (20 дерева, 10 заліза)","Побудувати гараж (35 дерева, 25 каменю, 15 заліза)","Виготовити вантажівку (20 дерева, 15 заліза, 60 монет)"},(d,which)->craft(which))
            .setNegativeButton("Назад",null).show();
    }
    private void craft(int kind){
        int w=0,st=0,ir=0,c=0;
        if(kind==0){if(carryUpgrade>0){msg("Героя вже покращено");return;}w=10;st=5;}
        if(kind==1){if(cartLevel>0){msg("Тачка вже є");return;}w=15;ir=5;}
        if(kind==2){if(cartLevel!=1){msg("Спочатку виготовіть звичайну тачку");return;}w=20;ir=10;}
        if(kind==3){if(garage){msg("Гараж уже побудовано");return;}w=35;st=25;ir=15;}
        if(kind==4){if(!garage||truck){msg("Спочатку побудуйте гараж або вантажівка вже є");return;}w=20;ir=15;c=60;}
        if(wood<w||stone<st||iron<ir||coins<c){msg("Недостатньо ресурсів на складі");return;}
        wood-=w;stone-=st;iron-=ir;coins-=c;
        if(kind==0)carryUpgrade=1;
        if(kind==1)cartLevel=1;
        if(kind==2)cartLevel=2;
        if(kind==3)garage=true;
        if(kind==4)truck=true;
        save();refresh();msg("Виготовлено! Вантажопідйомність: "+capacity());
    }
    private SharedPreferences prefs;
    private MapView map;
    private TextView status, objective;
    private final TextView[] resourceValues=new TextView[5];
    private int activePanel=0;
    private static final String[] VEHICLES={"Пішки","Велосипед","Мотоцикл","Автомобіль","Вантажівка"};
    private static final int[] SPEED={1,2,3,4,2};
    private static final int[] COST={0,55,150,360,650};
    private static final int BG=Color.rgb(236,242,229);

    @Override public void onCreate(Bundle state){super.onCreate(state);prefs=getSharedPreferences("kopanka_133_adventure_v1",MODE_PRIVATE);initTerrain();load();reveal(hero);buildUi();refresh();}
    // Stable, region-based geography: forests, quarries, two ore ranges, river and sea.
    private double region(double x,double y,double cx,double cy,double rx,double ry){
        double dx=(x-cx)/rx,dy=(y-cy)/ry;return dx*dx+dy*dy;
    }
    private void initTerrain(){
        for(int y=0;y<H;y++)for(int x=0;x<W;x++){
            int i=y*W+x;
            double wave=Math.sin(x*.37+y*.19)*1.2+Math.sin(y*.43-x*.13)*.8;
            // A broad southern sea, with a varying coastline.
            if(y>41+2*Math.sin(x*.21)){terrain[i]=4;continue;}
            // The winding north-to-south river joins the sea.
            double riverX=25+5*Math.sin(y*.16)+2*Math.sin(y*.39);
            if(Math.abs(x-riverX)<1.0+(y>36?1.0:0)){terrain[i]=4;continue;}
            // Two large mountain ranges rich in ore.
            if(region(x,y,9,12,7,8)<1.0 || region(x,y,39,17,6,10)<1.0){terrain[i]=3;continue;}
            // Only three concentrated stone quarry districts.
            if(region(x,y,13,34,3.4,3.2)<1 || region(x,y,36,32,3.8,3.0)<1 || region(x,y,19,8,2.7,2.8)<1){terrain[i]=2;continue;}
            // Continuous forests, with narrow natural trails.
            boolean forest=region(x,y,10,24,10,7)<1.0 || region(x,y,37,8,8,7)<1.0 || region(x,y,35,35,7,5)<1.0;
            if(forest){terrain[i]=((x+2*y)%13==0 || (2*x-y)%19==0)?0:1;continue;}
            terrain[i]=wave>1.55?5:0;
        }
        // Safe starting meadow and nearby resources.
        for(int dy=-2;dy<=2;dy++)for(int dx=-2;dx<=2;dx++)terrain[START+dy*W+dx]=0;
        terrain[START-3]=1;terrain[START+3]=1;
    }
    private void load(){
        boolean oldMap=!prefs.getBoolean("world_48_migrated",false);
        int oldHero=prefs.getInt("hero",15*30+15);
        hero=oldMap?((oldHero/30+9)*W+(oldHero%30+9)):prefs.getInt("hero",START);
        if(hero<0||hero>=N)hero=START;
        coins=prefs.getInt("coins",0);wood=prefs.getInt("wood",0);stone=prefs.getInt("stone",0);iron=prefs.getInt("iron",0);
        stage=Math.max(1,Math.min(3,prefs.getInt("stage",1)));vehicle=Math.max(0,Math.min(4,prefs.getInt("vehicle",0)));
        energy=prefs.getInt("energy",65);deliveries=prefs.getInt("deliveries",0);lastDay=prefs.getLong("day",0);
        cargoWood=prefs.getInt("cargoWood",0);cargoStone=prefs.getInt("cargoStone",0);cargoIron=prefs.getInt("cargoIron",0);
        carryUpgrade=prefs.getInt("carryUpgrade",0);cartLevel=prefs.getInt("cartLevel",0);
        garage=prefs.getBoolean("garage",false);truck=prefs.getBoolean("truck",false);
        if(!prefs.getBoolean("logistics_14_migrated",false)){energy=Math.max(energy,65);prefs.edit().putBoolean("logistics_14_migrated",true).apply();}
        for(int i=0;i<N;i++){
            int x=i%W,y=i/W;
            int oldIndex=(x>=9&&x<39&&y>=9&&y<39)?(y-9)*30+(x-9):-1;
            // Retain old exploration and roads, but avoid claiming a different resource type.
            String key=""+i;
            if(oldMap && oldIndex>=0)key=""+oldIndex;
            if(oldMap && oldIndex<0)continue;
            deposit[i]=prefs.getInt("deposit"+key,0);
            seen[i]=prefs.getBoolean("seen"+key,false);
            roads[i]=prefs.getBoolean("road"+key,false);
            claimed[i]=oldMap?false:prefs.getBoolean("claimed"+key,false);
            cleared[i]=prefs.getBoolean("clear"+key,false);
            infrastructure[i]=oldMap?0:prefs.getInt("infra"+key,0);
            infraLevel[i]=prefs.getInt("infraLevel"+key,1);
            builtAt[i]=prefs.getLong("built"+key,0);
        }
        if(oldMap){
            // Clear old deposit stockpiles, which belonged to different terrain.
            Arrays.fill(deposit,0);
            prefs.edit().putBoolean("world_48_migrated",true).apply();
        }
        Calendar cal=Calendar.getInstance();
        long today=cal.get(Calendar.YEAR)*1000L+cal.get(Calendar.DAY_OF_YEAR);
        if(lastDay!=today){energy=65+stage*5;lastDay=today;}
        save();
    }
    private void save(){
        SharedPreferences.Editor e=prefs.edit().putInt("hero",hero).putInt("coins",coins).putInt("wood",wood).putInt("stone",stone)
            .putInt("iron",iron).putInt("stage",stage).putInt("vehicle",vehicle).putInt("energy",energy)
            .putInt("deliveries",deliveries).putLong("day",lastDay)
            .putInt("cargoWood",cargoWood).putInt("cargoStone",cargoStone).putInt("cargoIron",cargoIron)
            .putInt("carryUpgrade",carryUpgrade).putInt("cartLevel",cartLevel)
            .putBoolean("garage",garage).putBoolean("truck",truck);
        for(int i=0;i<N;i++)e.putInt("deposit"+i,deposit[i]).putBoolean("seen"+i,seen[i]).putBoolean("road"+i,roads[i]).putBoolean("claimed"+i,claimed[i]).putBoolean("clear"+i,cleared[i]).putInt("infra"+i,infrastructure[i]).putInt("infraLevel"+i,infraLevel[i]).putLong("built"+i,builtAt[i]);e.apply();
    }
    private void reveal(int pos){int x=pos%W,y=pos/W;for(int dy=-1;dy<=1;dy++)for(int dx=-1;dx<=1;dx++){
        int nx=x+dx,ny=y+dy;if(nx>=0&&ny>=0&&nx<W&&ny<H)seen[ny*W+nx]=true;
    }}
    private int discovered(){int n=0;for(boolean b:seen)if(b)n++;return n;}
    private int claimedCount(){int n=0;for(boolean b:claimed)if(b)n++;return n;}
    private boolean adjacent(int a,int b){return Math.abs(a%W-b%W)<=1&&Math.abs(a/W-b/W)<=1&&a!=b;}
    // Plan using known terrain only. Unknown cells are provisionally passable.
    private List<Integer> route(int dest){
        int[] prev=new int[N];Arrays.fill(prev,-2);ArrayDeque<Integer> q=new ArrayDeque<>();q.add(hero);prev[hero]=-1;
        while(!q.isEmpty()){
            int cur=q.remove();if(cur==dest)break;
            int cx=cur%W,cy=cur/W;
            for(int dy=-1;dy<=1;dy++)for(int dx=-1;dx<=1;dx++){
                if(dx==0&&dy==0)continue;
                int nx=cx+dx,ny=cy+dy;if(nx<0||ny<0||nx>=W||ny>=H)continue;
                int ni=ny*W+nx;
                if(prev[ni]!=-2|| (seen[ni]&&terrain[ni]==4&&infrastructure[ni]==0))continue;
                prev[ni]=cur;q.add(ni);
            }
        }
        List<Integer> out=new ArrayList<>();if(prev[dest]==-2)return out;
        for(int i=dest;i!=hero;i=prev[i])out.add(0,i);return out;
    }
    private boolean isThicket(int tile){return terrain[tile]==1 && ((tile*13+7)%19==0);}
    private boolean isPass(int tile){return terrain[tile]==5 && ((tile*7+3)%5==0);}
    private boolean obstacle(int tile){return terrain[tile]==4||isPass(tile)||(isThicket(tile)&&!cleared[tile]);}
    private int wear(int tile){
        if(infrastructure[tile]==0)return 100;
        long days=Math.max(0,(System.currentTimeMillis()-builtAt[tile])/86400000L);
        return (int)Math.max(10,100-days*6);
    }
    private int travelCost(int tile){
        int cost=Math.max(1,(terrain[tile]==5?3:terrain[tile]==1?2:1)-Math.min(2,vehicle/2));
        if(infrastructure[tile]!=0){int w=wear(tile);cost+=w<30?7:w<65?3:0;cost=Math.max(1,cost-Math.max(0,infraLevel[tile]-1));}
        return cost;
    }
    private void tapTile(int tile){
        if(walking){msg("Герой уже рухається");return;}
        // A second tap on the marked destination confirms movement without a dialog.
        if(tile==target && !planned.isEmpty()){startWalking();return;}
        if(tile==START){
            new AlertDialog.Builder(this).setTitle("Поселення")
                .setItems(new String[]{"Відкрити", "Перейти"},(d,which)->{
                    if(which==0)showPanel(1);else planRoute(START);
                }).setNegativeButton("Скасувати",null).show();return;
        }
        if(tile==hero){showTile(tile);return;}
        planRoute(tile);
    }
    private void planRoute(int tile){
        List<Integer> path=route(tile);
        if(path.isEmpty()){msg("Немає відомого маршруту. Спробуйте інший шлях.");return;}
        target=tile;planned.clear();planned.addAll(path);map.invalidate();
        // The cross on the destination is the confirmation control.
        // Tap another tile to change the route.
    }
    private void clearRoute(){target=-1;planned.clear();if(map!=null)map.invalidate();}
    private void startWalking(){
        if(planned.isEmpty())return;
        walking=true;walkStep();
    }
    private void walkStep(){
        if(!walking)return;
        if(planned.isEmpty()){walking=false;clearRoute();save();refresh();showTile(hero);return;}
        int next=planned.get(0);
        // A newly revealed obstacle stops the hero before entering it.
        if(!seen[next]&&obstacle(next)){
            seen[next]=true;walking=false;save();refresh();
            obstacleDialog(next);return;
        }
        if(obstacle(next)&&terrain[next]==4&&infrastructure[next]==0){walking=false;obstacleDialog(next);return;}
        if(obstacle(next)&&isPass(next)&&infrastructure[next]==0){walking=false;obstacleDialog(next);return;}
        if(obstacle(next)&&isThicket(next)&&!cleared[next]){walking=false;obstacleDialog(next);return;}
        int cost=travelCost(next);
        if(energy<cost){walking=false;save();refresh();msg("Бракує часу. Маршрут залишився на карті.");return;}
        energy-=cost;hero=next;planned.remove(0);reveal(hero);save();refresh();if(hero==START)unload();
        movementHandler.postDelayed(()->walkStep(),240);
    }
    private void obstacleDialog(int tile){
        String kind=terrain[tile]==4?"Річка":isPass(tile)?"Гірський прохід":"Хащі";
        String action=terrain[tile]==4?"Зробити переправу":isPass(tile)?"Прокласти тунель":"Прорубати";
        int cost=terrain[tile]==4?6:isPass(tile)?7:4;
        new AlertDialog.Builder(this).setTitle("Перешкода: "+kind)
            .setMessage("Герой зупинився перед перешкодою.\n"+action+": "+cost+" часу.\nАбо оберіть інший шлях.")
            .setPositiveButton(action,(d,w)->{
                if(energy<cost){msg("Недостатньо часу");return;}
                energy-=cost;
                if(terrain[tile]==4)infrastructure[tile]=1;
                else if(isPass(tile))infrastructure[tile]=2;
                else cleared[tile]=true;
                if(infrastructure[tile]!=0)infraLevel[tile]=1;
                builtAt[tile]=System.currentTimeMillis();save();refresh();
                if(!planned.isEmpty()){walking=true;walkStep();}
            })
            .setNeutralButton("Обхід",(d,w)->{
                // Detour is chosen by selecting another tile, rather than auto-routing into unknown terrain.
                clearRoute();msg("Оберіть іншу точку на карті для обходу");
            }).setNegativeButton("Зупинитись",null).show();
    }
    private void showTile(int tile){
        if(tile==START){unload();showPanel(1);return;}
        String name=terrain[tile]==1?"Ліс":terrain[tile]==2?"Кам'яний кар'єр":terrain[tile]==3?"Родовище заліза":terrain[tile]==4?"Озеро":terrain[tile]==5?"Пагорби":"Луки";
        String desc=claimed[tile]?"Освоєно": "Ще не освоєно";
        AlertDialog.Builder b=new AlertDialog.Builder(this).setTitle(name).setMessage(desc+"\nНа ділянці: "+deposit[tile]+" од.\n"+cargoText()+"\nГерой: "+VEHICLES[vehicle]);
        if(tile==hero&&terrain[tile]>=1&&terrain[tile]<=3&&!claimed[tile]){
            b.setPositiveButton("Освоїти",(d,w)->{
                if(energy<2){msg("Потрібно 2 одиниці часу");return;}
                energy-=2;claimed[tile]=true;
                deposit[tile]+=terrain[tile]==1?12:terrain[tile]==2?10:6;
                msg("Об'єкт освоєно. Перша партія на ділянці — завантажте її.");save();refresh();showTile(tile);
            });
        }else if(tile==hero&&claimed[tile]&&terrain[tile]>=1&&terrain[tile]<=3){
            b.setPositiveButton("Видобути",(d,w)->gather(tile,terrain[tile]==1?8:terrain[tile]==2?6:4));
        }
        if(tile==hero&&claimed[tile]&&terrain[tile]>=1&&terrain[tile]<=3&&deposit[tile]>0){
            b.setNeutralButton("Завантажити",(d,w)->loadCargo(tile));
        }else if(tile==hero&&infrastructure[tile]!=0){
            b.setNeutralButton("Споруда",(d,w)->structureMenu(tile));
        }else if(tile==hero&&!roads[tile]&&terrain[tile]!=4){b.setNeutralButton("Дорога",(d,w)->buildRoad(tile));}
        b.setNegativeButton("Закрити",null).show();
    }
    private void buildRoad(int tile){if(wood<5||stone<3){msg("Дорога потребує 5 деревини й 3 каменю");return;}
        wood-=5;stone-=3;roads[tile]=true;save();refresh();msg("Дорогу побудовано");}
    private void structureMenu(int tile){
        new AlertDialog.Builder(this).setTitle(infrastructure[tile]==1?"Міст":"Тунель")
            .setMessage("Рівень: "+infraLevel[tile]+"/3\nСтан: "+wear(tile)+"%\nРемонт: 4 деревини, 4 каменю\nПокращення: 12 деревини, 12 каменю, 15 монет")
            .setPositiveButton("Ремонт",(d,w)->repair(tile))
            .setNeutralButton("Покращити",(d,w)->upgradeStructure(tile))
            .setNegativeButton("Назад",null).show();
    }
    private void upgradeStructure(int tile){
        if(infraLevel[tile]>=3){msg("Максимальний рівень");return;}
        if(wood<12||stone<12||coins<15){msg("Недостатньо ресурсів");return;}
        wood-=12;stone-=12;coins-=15;infraLevel[tile]++;
        builtAt[tile]=System.currentTimeMillis();save();refresh();msg("Споруду вдосконалено");
    }
    private void repair(int tile){
        if(wood<4||stone<4){msg("Ремонт: 4 деревини та 4 каменю");return;}
        wood-=4;stone-=4;builtAt[tile]=System.currentTimeMillis();save();refresh();msg("Споруду відремонтовано");
    }
    private void msg(String s){Toast.makeText(this,s,Toast.LENGTH_LONG).show();}
    private TextView text(String s,int size){TextView t=new TextView(this);t.setText(s);t.setTextColor(Color.rgb(30,51,42));t.setTextSize(size);t.setPadding(12,8,12,8);return t;}
    private Button button(String s,Runnable r){Button b=new Button(this);b.setText(s);b.setTextSize(12);b.setAllCaps(false);b.setOnClickListener(v->r.run());return b;}
    private TextView overlayText(String value,int size){
        TextView t=text(value,size);t.setBackgroundColor(0xEAF2F6E9);return t;
    }
    private void buildUi(){
        FrameLayout screen=new FrameLayout(this);screen.setBackgroundColor(BG);
        // Keep controls clear of the Android status/navigation bars, including edge-to-edge devices.
        screen.setOnApplyWindowInsetsListener((view,insets)->{
            view.setPadding(insets.getSystemWindowInsetLeft(),insets.getSystemWindowInsetTop(),
                insets.getSystemWindowInsetRight(),insets.getSystemWindowInsetBottom());
            return insets;
        });
        map=new MapView();screen.addView(map,new FrameLayout.LayoutParams(-1,-1));
        objective=overlayText("",11);objective.setSingleLine(false);
        FrameLayout.LayoutParams objectiveParams=new FrameLayout.LayoutParams(-1,-2,Gravity.TOP);
        objectiveParams.leftMargin=dp(3);objectiveParams.rightMargin=dp(3);
        // Top exploration banner intentionally hidden for an unobstructed map.
        LinearLayout left=new LinearLayout(this);left.setOrientation(LinearLayout.VERTICAL);
        String[] leftNames={"Завдання","Поселення","Транспорт","Ресурси","Торгівля","Герой"};
        String[] leftIcons={"☷","⌂","▣","◆","⇄","⌖"};
        for(int i=0;i<leftNames.length;i++)addMenuButton(left,leftIcons[i],leftNames[i],i);
        FrameLayout.LayoutParams lp=new FrameLayout.LayoutParams(dp(83),-2,Gravity.LEFT|Gravity.CENTER_VERTICAL);
        screen.addView(left,lp);
        LinearLayout right=new LinearLayout(this);right.setOrientation(LinearLayout.VERTICAL);
        right.setPadding(dp(2),dp(3),dp(2),dp(3));right.setBackgroundColor(0xC9233B34);
        String[] icons={"🪵","🪨","⛓","🪙","⌛"};
        for(int i=0;i<icons.length;i++){
            TextView value=new TextView(this);value.setTextColor(Color.WHITE);value.setTextSize(12);
            value.setSingleLine(true);value.setGravity(Gravity.CENTER_VERTICAL|Gravity.CENTER_HORIZONTAL);
            value.setText(icons[i]+" 0");resourceValues[i]=value;
            right.addView(value,new LinearLayout.LayoutParams(-1,dp(29)));
        }
        FrameLayout.LayoutParams rp=new FrameLayout.LayoutParams(dp(60),-2,Gravity.RIGHT|Gravity.CENTER_VERTICAL);
        screen.addView(right,rp);
        setContentView(screen);
        screen.requestApplyInsets();
    }
    private void addMenuButton(LinearLayout column,String icon,String name,int id){
        TextView v=new TextView(this);v.setText(icon+" "+name);v.setTextColor(0xFF23463D);
        v.setTextSize(10);v.setTypeface(null,Typeface.BOLD);v.setGravity(Gravity.CENTER);
        v.setIncludeFontPadding(false);v.setPadding(dp(2),0,dp(2),0);
        v.setSingleLine(true);v.setBackgroundColor(0xEAF2F6E9);
        LinearLayout.LayoutParams p=new LinearLayout.LayoutParams(-1,dp(32));p.setMargins(dp(1),dp(1),dp(1),dp(1));
        column.addView(v,p);
        v.setOnClickListener(view->{if(id==5){map.centerOnHero();}else showPanel(id);});
    }
    private int dp(float value){return (int)(value*getResources().getDisplayMetrics().density+0.5f);}
    private void refresh(){
        if(objective==null)return;
        int[] values={wood,stone,iron,coins,energy};
        String[] icons={"🪵","🪨","⛓","🪙","⌛"};
        for(int i=0;i<resourceValues.length;i++)if(resourceValues[i]!=null)resourceValues[i].setText(icons[i]+" "+values[i]);
        String task=claimedCount()==0?"Дослідіть і освоїте перший ліс або кар'єр":
            deliveries==0?"Зберіть ресурси й виконайте перше замовлення":
            stage<3?"Розвивайте поселення та відкривайте нові території":"Дослідіть карту й розширюйте торговельну мережу";
        objective.setText("🎯 "+task+" · Відкрито "+discovered()+"/"+N+" · Час до завтра");
        if(map!=null)map.invalidate();
    }
    private void showPanel(int id){
        if(id==0)new AlertDialog.Builder(this).setTitle("Завдання").setMessage(
            "1. Освоїти ресурси: "+claimedCount()+" об'єктів\n2. Доставити товари: "+deliveries+" рейсів\n3. Відкрити карту: "+discovered()+"/"+N+
            "\n\nДослідження витрачає час. Запас відновлюється наступного дня.").setPositiveButton("До карти",null).show();
        if(id==1){
            String req=stage==1?"20 деревини, 15 каменю, 35 монет":"50 деревини, 35 каменю, 100 монет";
            new AlertDialog.Builder(this).setTitle("Поселення · рівень "+stage+"/3")
                .setMessage((stage==3?"Максимальний рівень.":"Наступний рівень: "+req)+"\n\n"+cargoText()+"\nДоставте вантаж сюди для розвантаження.")
                .setPositiveButton("Майстерня",(d,w)->logisticsMenu())
                .setNeutralButton(stage==3?"Розвантажити":"Покращити",(d,w)->{if(stage<3)upgrade();else unload();})
                .setNegativeButton("Назад",null).show();
        }
        if(id==2){
            StringBuilder sb=new StringBuilder("Зараз: "+VEHICLES[vehicle]+"\nШвидкість: "+SPEED[vehicle]+"×\n");
            if(vehicle<4)sb.append("Наступний транспорт: ").append(VEHICLES[vehicle+1]).append("\nЦіна: ").append(COST[vehicle+1]).append(" монет");
            else sb.append("Увесь транспорт відкрито");
            new AlertDialog.Builder(this).setTitle("Транспорт").setMessage(sb.toString())
                .setPositiveButton(vehicle==4?"Гаразд":"Придбати",(d,w)->buyVehicle()).setNegativeButton("Назад",null).show();
        }
        if(id==3)new AlertDialog.Builder(this).setTitle("Ресурси").setMessage(
            "СКЛАД ПОСЕЛЕННЯ\nДеревина: "+wood+"\nКамінь: "+stone+"\nЗалізо: "+iron+"\n\n"+cargoText()+
            "\n\nДля видобутку вирушайте до освоєного об'єкта. Дороги коштують 5 деревини й 3 каменю.")
            .setPositiveButton("Гаразд",null).show();
        if(id==4)new AlertDialog.Builder(this).setTitle("Торгівля")
            .setMessage("Контракт 1: 10 деревини → 25 монет\nКонтракт 2: 8 каменю → 30 монет\nКонтракт 3: 5 заліза → 45 монет")
            .setPositiveButton("Деревина",(d,w)->trade(0)).setNeutralButton("Камінь",(d,w)->trade(1))
            .setNegativeButton("Залізо",(d,w)->trade(2)).show();
    }
    private void upgrade(){if(stage>=3)return;int w=stage==1?20:50,s=stage==1?15:35,c=stage==1?35:100;
        if(wood<w||stone<s||coins<c){msg("Недостатньо ресурсів або монет");return;}
        wood-=w;stone-=s;coins-=c;stage++;save();refresh();msg("Поселення досягло рівня "+stage);}
    private void buyVehicle(){if(vehicle>=4)return;if(coins<COST[vehicle+1]){msg("Недостатньо монет");return;}
        coins-=COST[vehicle+1];vehicle++;save();refresh();msg("Новий транспорт: "+VEHICLES[vehicle]);}
    private void trade(int type){int qty=type==0?10:type==1?8:5;int reward=type==0?25:type==1?30:45;
        int have=type==0?wood:type==1?stone:iron;
        if(have<qty){msg("Недостатньо товару для контракту");return;}
        if(type==0)wood-=qty;else if(type==1)stone-=qty;else iron-=qty;
        coins+=reward;deliveries++;save();refresh();msg("Доставлено! +"+reward+" монет");}

    private class MapView extends View{
        Paint p=new Paint(3);float tileW,tileH,ox,oy;
        void centerOnHero(){
            if(getWidth()==0 || getHeight()==0){centerPending=true;return;}
            float w=getWidth(),h=getHeight();
            float tw=Math.min(w/(12*.76f),h/(12*.46f)),th=tw*.54f;
            float hx=w*.5f+(hero%W-hero/W)*tw*.5f;
            float hy=h*.5f-(W+H)*th*.25f+(hero%W+hero/W)*th*.5f;
            panX=zoom*(w*.5f-hx);panY=zoom*(h*.52f-hy);invalidate();
        }
        float panX=0,panY=0,zoom=1.6f,downX,downY,lastX,lastY;
        boolean moved=false,multiTouch=false,centerPending=true;
        @Override protected void onSizeChanged(int w,int h,int oldw,int oldh){
            super.onSizeChanged(w,h,oldw,oldh);
            if(centerPending){centerPending=false;centerOnHero();}
        }
        MapView(){super(MainActivity.this);setLayerType(View.LAYER_TYPE_SOFTWARE,null);}
        // KOPANKA 1.9: continuous world surface; cells are only logical coordinates.
        private float worldX(float x,float y){return ox+(x-y)*tileW*.5f;}
        private float worldY(float x,float y){return oy+(x+y)*tileH*.5f;}
        private void smoothStroke(Canvas c,Path path,int color,float width){
            p.setStyle(Paint.Style.STROKE);p.setStrokeCap(Paint.Cap.ROUND);
            p.setStrokeJoin(Paint.Join.ROUND);p.setStrokeWidth(width);p.setColor(color);
            c.drawPath(path,p);p.setStyle(Paint.Style.FILL);
        }
        private Path riverPath(){
            Path river=new Path();
            for(int y=0;y<H;y++){
                float x=(float)(25+5*Math.sin(y*.16)+2*Math.sin(y*.39));
                float sx=worldX(x,y),sy=worldY(x,y);
                if(y==0)river.moveTo(sx,sy);else river.lineTo(sx,sy);
            }
            return river;
        }
        private void drawWorld(Canvas c){
            // Uniform grass under all regions: no tile boundaries or diamond grid.
            p.setColor(0xFF92A975);
            Path land=new Path();land.moveTo(worldX(-.5f,-.5f),worldY(-.5f,-.5f));
            land.lineTo(worldX(W-.5f,-.5f),worldY(W-.5f,-.5f));
            land.lineTo(worldX(W-.5f,H-.5f),worldY(W-.5f,H-.5f));
            land.lineTo(worldX(-.5f,H-.5f),worldY(-.5f,H-.5f));land.close();c.drawPath(land,p);
            // Broad soft patches add landscape variation without exposing navigation cells.
            for(int y=2;y<H;y+=4)for(int x=2;x<W;x+=4){
                float sx=worldX(x,y),sy=worldY(x,y);
                p.setColor(((x*11+y*7)%3==0)?0x1590C07C:0x12717D54);
                c.drawOval(new RectF(sx-tileW*1.6f,sy-tileH*.9f,sx+tileW*1.6f,sy+tileH*.9f),p);
            }
            // River and banks: one continuous winding watercourse, not blue diamonds.
            Path river=riverPath();
            smoothStroke(c,river,0xFF66775B,tileW*1.23f);
            smoothStroke(c,river,0xFF4C8491,tileW*1.04f);
            smoothStroke(c,river,0xFF5C9BA5,tileW*.77f);
            // Sea is a continuous southern region, with an irregular coastline.
            Path sea=new Path();
            for(int x=0;x<W;x++){
                float y=(float)(41+2*Math.sin(x*.21));
                if(x==0)sea.moveTo(worldX(x,y),worldY(x,y));
                else sea.lineTo(worldX(x,y),worldY(x,y));
            }
            sea.lineTo(worldX(W-1,H+1),worldY(W-1,H+1));
            sea.lineTo(worldX(-1,H+1),worldY(-1,H+1));sea.close();
            p.setColor(0xFF518B9B);c.drawPath(sea,p);
        }
        @Override protected void onDraw(Canvas c){super.onDraw(c);c.drawColor(0xFF20332D);
            float width=getWidth(),height=getHeight();
            c.save();c.translate(panX,panY);c.scale(zoom,zoom,width*.5f,height*.5f);
            tileW=Math.min(width/(12*.76f),height/(12*.46f));tileH=tileW*.54f;
            ox=width*.5f;oy=height*.5f-(W+H)*tileH*.25f;
            // Exploration is a soft-edged union of circles; the hidden grid is never drawn.
            Path visible=new Path();
            for(int i=0;i<N;i++)if(seen[i]){
                int x=i%W,y=i/W;
                visible.addOval(new RectF(worldX(x,y)-tileW*.70f,worldY(x,y)-tileH*.83f,
                    worldX(x,y)+tileW*.70f,worldY(x,y)+tileH*.83f),Path.Direction.CW);
            }
            c.save();c.clipPath(visible);
            drawWorld(c);
            // Render terrain objects after the ground, back-to-front for depth.
            for(int sum=0;sum<W+H-1;sum++)for(int y=0;y<H;y++){
                int x=sum-y;if(x<0||x>=W)continue;int i=y*W+x;
                if(!seen[i])continue;
                float sx=worldX(x,y),sy=worldY(x,y);
                if(roads[i]){p.setColor(0xFFB49A70);p.setStrokeWidth(tileW*.13f);c.drawLine(sx-tileW*.2f,sy,sx+tileW*.2f,sy,p);}
                if(i==START){p.setColor(0xFF7F5437);c.drawRect(sx-tileW*.18f,sy-tileH*.4f,sx+tileW*.18f,sy+tileH*.12f,p);
                    p.setColor(0xFFC05B3D);Path roof=new Path();roof.moveTo(sx-tileW*.24f,sy-tileH*.38f);roof.lineTo(sx,sy-tileH*.86f);roof.lineTo(sx+tileW*.24f,sy-tileH*.38f);roof.close();c.drawPath(roof,p);
                }else if(terrain[i]==1){forestMass(c,sx,sy,x,y);
                }else if(terrain[i]==2){mountain(c,sx,sy,false,x,y);
                }else if(terrain[i]==3){mountain(c,sx,sy,true,x,y);
                }else if(terrain[i]==5){p.setColor(0xFF758F61);c.drawOval(new RectF(sx-tileW*.31f,sy-tileH*.32f,sx+tileW*.31f,sy+tileH*.12f),p);}
                if(deposit[i]>0){p.setColor(0xFFF4EAAE);p.setTextSize(tileW*.17f);p.setTextAlign(Paint.Align.CENTER);c.drawText(""+deposit[i],sx,sy+tileH*.45f,p);}
                if(claimed[i]){p.setColor(0xFFF9CE5B);c.drawCircle(sx+tileW*.21f,sy-tileH*.35f,tileW*.065f,p);}
                if(i==hero){
                    if(cartLevel>0||truck){p.setColor(0xFF784E2B);c.drawRect(sx+tileW*.12f,sy-tileH*.25f,sx+tileW*.37f,sy-tileH*.05f,p);p.setColor(Color.DKGRAY);c.drawCircle(sx+tileW*.17f,sy,tileW*.035f,p);c.drawCircle(sx+tileW*.33f,sy,tileW*.035f,p);}
                    p.setColor(0xFF27405C);c.drawCircle(sx,sy-tileH*.55f,tileW*.12f,p);
                    p.setColor(0xFFF2BF8C);c.drawCircle(sx,sy-tileH*.84f,tileW*.073f,p);
                    p.setColor(Color.WHITE);p.setTextSize(tileW*.17f);p.setTextAlign(Paint.Align.CENTER);c.drawText("●",sx,sy-tileH*.95f,p);
                }
            }
            c.restore();
            drawPlannedRoute(c);
            c.restore();
        }
        private void drawPlannedRoute(Canvas c){
            if(target<0)return;
            p.setStyle(Paint.Style.STROKE);p.setStrokeWidth(tileW*.075f);
            p.setPathEffect(new android.graphics.DashPathEffect(new float[]{tileW*.16f,tileW*.12f},0));
            float lastX=ox+(hero%W-hero/W)*tileW*.5f;
            float lastY=oy+(hero%W+hero/W)*tileH*.5f;
            int time=energy;
            for(int step:planned){
                float sx=ox+(step%W-step/W)*tileW*.5f;
                float sy=oy+(step%W+step/W)*tileH*.5f;
                time-=travelCost(step);
                p.setColor(time>=0?0xFFFFFFFF:0x66FFFFFF);
                c.drawLine(lastX,lastY,sx,sy,p);
                lastX=sx;lastY=sy;
            }
            p.setPathEffect(null);p.setStyle(Paint.Style.FILL);
            p.setColor(time>=0?0xFFFFFFFF:0x66FFFFFF);
            p.setStrokeWidth(tileW*.11f);p.setStrokeCap(Paint.Cap.ROUND);
            c.drawLine(lastX-tileW*.16f,lastY-tileH*.25f,lastX+tileW*.16f,lastY+tileH*.25f,p);
            c.drawLine(lastX-tileW*.16f,lastY+tileH*.25f,lastX+tileW*.16f,lastY-tileH*.25f,p);
        }
        // The diamond remains the invisible navigation cell; the artwork reads as continuous terrain.
private void forestMass(Canvas c,float x,float y,int gx,int gy){
            // Overlapping canopy: forest reads as a single mass with natural clearings.
            float wiggle=((gx*17+gy*23)%7-3)*tileW*.012f;
            p.setColor(0xFF244E37);
            c.drawOval(new RectF(x-tileW*.39f,y-tileH*.58f,x+tileW*.39f,y+tileH*.19f),p);
            p.setColor(0xFF326A45);
            c.drawCircle(x-tileW*.19f,y-tileH*.30f,tileW*.22f,p);
            c.drawCircle(x+tileW*.17f,y-tileH*.37f,tileW*.23f,p);
            p.setColor((gx+gy)%3==0?0xFF52865A:0xFF3C7750);
            c.drawCircle(x+wiggle,y-tileH*.54f,tileW*.20f,p);
            if((gx*5+gy*3)%11==0){p.setColor(0xFF78A46B);
                c.drawCircle(x-tileW*.09f,y-tileH*.57f,tileW*.075f,p);}
        }
        private void mountain(Canvas c,float x,float y,boolean ore,int gx,int gy){
            float height=ore?(1.05f+((gx*7+gy*3)%5)*.12f):(.58f+((gx*3+gy*5)%4)*.08f);
            p.setColor(0x553D4139);
            c.drawOval(new RectF(x-tileW*.38f,y-tileH*.11f,x+tileW*.38f,y+tileH*.22f),p);
            Path left=new Path();left.moveTo(x-tileW*.34f,y+tileH*.10f);
            left.lineTo(x-tileW*.035f,y-tileH*height);left.lineTo(x+tileW*.04f,y+tileH*.12f);
            left.close();p.setColor(ore?0xFF666F70:0xFF858B87);c.drawPath(left,p);
            Path right=new Path();right.moveTo(x-tileW*.035f,y-tileH*height);
            right.lineTo(x+tileW*.33f,y+tileH*.10f);right.lineTo(x+tileW*.04f,y+tileH*.12f);
            right.close();p.setColor(ore?0xFF414E56:0xFF626E70);c.drawPath(right,p);
            if(ore){Path peak=new Path();peak.moveTo(x-tileW*.035f,y-tileH*height);
                peak.lineTo(x-tileW*.12f,y-tileH*(height-.30f));
                peak.lineTo(x+tileW*.07f,y-tileH*(height-.28f));peak.close();
                p.setColor(0xFFC2C9C5);c.drawPath(peak,p);}
        }
        private float distance(MotionEvent e){
            float dx=e.getX(0)-e.getX(1),dy=e.getY(0)-e.getY(1);
            return (float)Math.hypot(dx,dy);
        }
         @Override public boolean onTouchEvent(MotionEvent e){
             int action=e.getActionMasked();
             if(action==MotionEvent.ACTION_DOWN){
                 downX=lastX=e.getX();downY=lastY=e.getY();moved=false;multiTouch=false;
                 return true;
             }
             if(action==MotionEvent.ACTION_POINTER_DOWN){multiTouch=true;moved=true;return true;}
             if(action==MotionEvent.ACTION_MOVE){
                 if(e.getPointerCount()!=1 || multiTouch)return true;
                 float x=e.getX(),y=e.getY();
                 if(Math.hypot(x-downX,y-downY)>dp(9))moved=true;
                 if(moved){panX+=x-lastX;panY+=y-lastY;invalidate();}
                 lastX=x;lastY=y;return true;
             }
             if(action==MotionEvent.ACTION_POINTER_UP){multiTouch=true;return true;}
             if(action==MotionEvent.ACTION_UP){
                 if(!moved&&!multiTouch){
                     float px=(e.getX()-getWidth()*.5f-panX)/zoom+getWidth()*.5f;
                     float py=(e.getY()-getHeight()*.5f-panY)/zoom+getHeight()*.5f;
                     float best=Float.MAX_VALUE;int pick=-1;
                     for(int y=0;y<H;y++)for(int x=0;x<W;x++){
                         float sx=ox+(x-y)*tileW*.5f,sy=oy+(x+y)*tileH*.5f;
                         float dx=(px-sx)/(tileW*.5f),dy=(py-sy)/(tileH*.5f);
                         float dist=Math.abs(dx)+Math.abs(dy);
                         if(dist<best){best=dist;pick=y*W+x;}
                     }
                     if(pick>=0&&best<1.1f)tapTile(pick);
                     performClick();
                 }
                 multiTouch=false;return true;
             }
             if(action==MotionEvent.ACTION_CANCEL){multiTouch=false;return true;}
             return true;
         }

        @Override public boolean performClick(){super.performClick();return true;}
    }
}
