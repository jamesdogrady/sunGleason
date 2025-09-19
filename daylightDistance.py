# this program determines a radius of daylight and nighttime on the earth.  Because the earth is spherical, daylight
# and nighttime should form circles on the planet, so this program tries to show that.
# Calculation of sunset/sunrise is done by the astral package.  This requires doing multiple queries to find the
# points we need, but I use the package because I've used this before, and the query is somewhat interesting.
# First, we start at point (0,0) for the given time and use the length of daylight on that day to calculate the 
# longtide at which it's solar noon.  We know that the sun be overhead at this longitude somewhere between the tropic
# of cancer and the tropic of capricorn.  we use the zenith function of astral and search for the lowest zenith. From
# this point, we can calculate the antipode of the noon point, which we expect to be the center of a circle of darkness

# for the non-polar regions, for each latitude, we use the length of day at the noon longitude to roughly calculate
# where the sun is rising and setting.  Because the sun is also moving between the tropics, the is an estimate and 
# we have to search for an exact point.
# in the polar regions, most times, there is 24 hour darkness or light.  If it's dark at a polar latitude, the edge of# circles we are looking for at the noon longitude and that latitude.  if it's light at a polar latitude, its light
# will end at that latidue at the antipode of the noon point, so use that.
# once we have all the points, we calculate the radius and do some analysis of the results.  
# 
# options:
# -t :timestamp.
# -l :increment between latidues.
# -d :debug
# -p : precision 
# -v: verbose:  print the points that we use for the edges of the circle.
# -a : assert_seconds:  we compare the actual time of sunset, sunrise and noon to what we are using.  We 
# discard a point if the test fails.
# -g: print distances for the actual geodesic earth
# -s:  print distances for a presumes spherical earth.

from astral.sun import sunrise,sunset,zenith
from astral import Observer
from astral.sun import zenith,noon 
from geopy.distance import geodesic,great_circle
import pandas as pd
import datetime
import sys
import pytz
import math
import numpy as np
import argparse;
import tabulate

utc=pytz.UTC
parser=argparse.ArgumentParser();
parser.add_argument("-t",'--timestamp',type=str,help="time Mon/Day/Year HH:MM");
parser.add_argument("-l",'--increment',type=str, help="how far between latitudes");
parser.add_argument("-d",'--debug',action='store_true',help="Debugging Outut");
parser.add_argument("-p",'--precision',type=str,help="how precise to be on calculated values. Default=.05");
parser.add_argument("-v","--verbose",action='store_true',help="Show points which outline each shape");
parser.add_argument("-a","--assert_seconds",type=str,help="Give an error if we aren't within seconds of the event");
parser.add_argument("-g",'--geodesic',action='store_true',help="Report actual distances");
parser.add_argument("-s",'--spherical',action='store_true',help="Report Great Circle distances");
args=parser.parse_args()

if "debug" in args and args.debug :
    debug=True;
else : 
    debug=False;
    
if "geodesic" in args and args.geodesic :
    report_geodesic=True
else:
    report_geodesic=False

if "spherical" in args and args.spherical:
    report_spherical=True
else:
    report_spherical=False

if "timestamp" in args and args.timestamp != None :
    tm= datetime.datetime.strptime(args.timestamp, "%m-%d-%Y %H:%M")
    tm=tm.astimezone(utc)
else:
    tm=datetime.datetime.now(tz=utc);

if "increment" in args and args.increment != None :
    lat_incr = int(args.increment);
else: 
    lat_incr = 10

dec_point=2
if "precision" in args and args.precision != None :
    # count digits after decimal point
    precision=float(args.precision);
    dot_index=args.precision.find('.');
    if dot_index != -1 :
        dec_point=len(args.precision[dot_index + 1:])
    else :
        dec_point=0;
else:
    precision=.05


if "assert_seconds" in args and args.assert_seconds != None :
    assert_seconds =int(args.assert_seconds);
else:
    assert_seconds = 30

if "verbose" in args and args.verbose:
    verbose=True
else :
    verbose=False

# by default, we ll report spherical if neither -s or -g is specified

if not  report_spherical and not report_geodesic :
        report_geodesic = True

yesterday = tm - datetime.timedelta(days=-1);
tommorrow = tm + datetime.timedelta(days=-1);
# -179 and 179 are two degrees apart so we do longitude math.
def conv_long(val) :
    if ( val > 180 ) :
        val = -180+(val - 180);
    if ( val < -180) :
            val = 180+(val + 180);
    return val

obs_lat=0
obs_long=0
obs=Observer(obs_lat,obs_long);
noon_tm=noon(obs,tm,tzinfo=utc);
dps=15/(60*60)
# calculate the longitude where it is noon currently.
# noon has either passed or is coming, so we can tell where it is.
if ( noon_tm > tm ) :
    # noon is coming.
    noon_time=(noon_tm - tm).seconds
    noon_long=obs_long + noon_time *dps
else :
    noon_time=(tm - noon_tm).seconds
    noon_long=obs_long - noon_time * dps

noon_long=conv_long(noon_long);


# function to search for a value between low and high.  If fcn returns True, exclude from midpoint to high
# if fcn returns False, exclude between low and midpoint.  fcn is a direction of travel.
# low, high and val can be either latitude or longitude.

def find_true_value(low,high ,val,tm,fcn) :
    done=False
    while not done :
        ret_bool = False;
        t=abs(high - low)
        # for longitude, if you are more than 180 apart, you are going the long way around.  
        if t > 180 :
            t=360-t
        diff = t/2
        if ( diff < precision  ) :
            return low
        mid = low+diff
        # this could be a latitude but it won't be that big
        if mid > 180 or mid < -180 :
            mid=conv_long(mid);
        (res,v) = fcn(mid,val,tm);
        if ( debug ) :
            print("find_true_value ",low,high,mid,val,res);
        if v != None and v :
            ret_bool=True
        if res :
            high=mid
        else :
            low=mid

# tropic of cancern is  23' 26 min
# these are not precise values.  They represent an endpoint that allows the search to work.
tropic_cancer=23.1
tropic_capricorn = -23.1
arctic_circle=66.2
antarctic_circle=-66.2

# we need to find the latitude at which it is noon.  Note that this must be between the tropic of cancer and the
#tropic of capricorn.
# we are looking for the lowest zenith we can find.

eq_obs=Observer(0,noon_long);
eq_zenith=zenith(eq_obs,tm);
north_obs= Observer(tropic_cancer,noon_long);
south_obs= Observer(tropic_capricorn,noon_long);
north_zen=zenith(north_obs,tm);
south_zen=zenith(south_obs,tm);

done=False
first=True
north_lat=tropic_cancer
south_lat = tropic_capricorn
# We can't use find_true_value here because functions can't tell whether the zenith is north or south of a point
# unless it has information about both endpoints.

while not done :
    # if the zenith is the same at both endpoints the correct value is in the middle.
    if north_zen == south_zen :
        noon_lat = (north_lat + south_lat) /2
        done=True

    # are we close enough to stop?
    diff = abs(abs(north_lat) - abs(south_lat))

    if (not first and diff < precision ) :
        noon_lat = north_lat
        done=True
    first=False;
    if ( north_zen < south_zen ) :
        # between center and south.
        south_lat = ( north_lat + south_lat)/2
        south_obs= Observer(south_lat,noon_long);
        south_zen=zenith(south_obs,tm)
    else :
        north_lat = ( north_lat + south_lat)/2
        north_obs= Observer(north_lat,noon_long);
        north_zen=zenith(north_obs,tm);

noon_obs=Observer(noon_lat,noon_long);

# antipode_lat 
anti_noon_lat= -1 * noon_lat
if ( noon_long < 0 ) :
    anti_noon_long=noon_long + 180;
else:
    anti_noon_long=noon_long - 180;

noon_point= ( noon_lat,noon_long);
anti_noon_point= ( anti_noon_lat,anti_noon_long);

if ( debug) :
    print("noon (",noon_lat, noon_long,")");
    print("anti_noon (",anti_noon_lat, anti_noon_long,")")


# helper function called by find_true_value to find the point where 24 hour dark or light starts.
# for the north, we start at the arctic circle and end at the north point.  Returning True moves us south
# returning False moves us north.  For the south, it's the reverse.
# this returns whether it's dark or light as it is also used as a utilty function elsewhere.

def twenty_4_hour(lat, long,tm) :
        obs= Observer(lat,long)
        noRise=False
        light=False;
        try :
            rise=sunrise(obs,tm);
            noRise=False
        except ValueError as e :
            noRise=True
            found_24_hour=True
            if "above" in e.args[0] :
                light=True;
            else:
                light=False;
        if ( lat < 0) :
            return( not noRise,light);
        return(noRise,light);

# funcion called by find_true_value to find whether the sun is up or down at the given latitude based on sunset
# long is the midpoint between the high and low.  Return True if it's after sunset as we move to the west to
# find the sunset.
# we have to consider crossing the midnight line in which case sunrise would be ater midnight./check_su
def after_sunset(long,lat,tm) :
    nine_hours = 9 * 3600
    obs=Observer(lat,long)
    try :
        set=sunset(obs,tm) 
        if ( tm < set) :
            if ( (set-tm).seconds > nine_hours ) :
                # check tommorrow.
                tommorrow = tm + datetime.timedelta(days=-1);
                set=sunset(obs,tommorrow) 
        if ( tm>set ) :
            return (True,None);
        else :
            return ( False,None);
    except ValueError as e:
        if "Unable to find a sunset time" in e.args[0] :
                # The sun sets  here after midnight on this day.
                if ( debug ) :
                    print("After sunset: after midnight",long,lat);
                return(True,None)
        if debug :
            print("after_sunset: Unexpected Exception",lat,long,e.args[0]);
        return (True,None);

# we are trying to find sunrise .  long is the midpoint between the west and east value.
# if the sun has risen, sunrise is to the west, if it has not, sunrise is to the east.
def before_sunrise(long,lat,tm) :
    nine_hours = 9 * 3600
    obs=Observer(lat,long)
    try :
        rise=sunrise(obs,tm) 
        if ( tm<rise ) :
            if ((  rise-tm).seconds > nine_hours  ) :
                    yesterday= tm + datetime.timedelta(days=-1);
                    rise=sunrise(obs,yesterday) 
        if ( tm>rise ) :
            return(True,None)
        else :
            return (False,None);
    except ValueError as e:
        if "Unable to find a sunrise time" in e.args[0] :
                # The sun rises tommorrow.
                print("Before sunset: after midnight",long,lat);
                return(True,None);
        if ( debug ) :
            print("before_sunrise: Unexpected Exception",lat,long,e.args[0]);
        return (True,None);




# find the latitude at which there is 24 darkness or light.  This is the endpoint for the shapes of daylight
# is is dark at the south pole.
(sp_24,sp_light) = twenty_4_hour(-90,0,tm) 
# is is dark at the north pole.
(np_24,np_light) = twenty_4_hour(90,0,tm) 
if ( not sp_24 ) :
    (south_lat)=find_true_value(-90,-65,noon_long,tm,twenty_4_hour);

if ( np_24 ) :
    (north_lat)  = find_true_value(65,90,noon_long,tm,twenty_4_hour);

north_light=np_light
south_light = sp_light


southern_light_point = None
northern_light_point = None
if sp_24 == True:
    south_lat=-90;
else :
    if (south_light) :
        # since there is 24 hour light in the south mark it around the pole.
        southern_light_point=(south_lat,anti_noon_long);
    else :
        southern_light_point=(south_lat,noon_long);
if np_24 == False :
    north_lat=-90;
else :
    if (north_light) :
        # since there is 24 hour light in the south mark it around the pole.
        northern_light_point=(north_lat,anti_noon_long);
    else :
        northern_light_point=(north_lat,noon_long);

if ( debug ) :
    print("Found ", north_light,north_lat,south_light,south_lat);

# assert function to see how close we are to noon
def check_noon(lat,long,tm) :
    lat_obs = Observer(lat,long)
    noon_time = noon(lat_obs,tm) 
    
    if ( noon_time > tm) :
        diff = noon_time - tm
    else:
        diff = tm - noon_time
    if ( debug) :
        print("check_noon (",lat,",",long,") ",diff.seconds," different");
    if ( diff.seconds < assert_seconds ) :
        return True;
    return False

# we might need to look at yesterday however.
def check_sunset(lat,long,tm) :
    s=" sun is up"
    if debug :
        print("check_sunset",lat,long);
    lat_obs = Observer(lat,long)
    set_time = sunset(lat_obs,tm) 
    if ( set_time > tm) :
        diff = set_time - tm
    else:
        s="sun has already set"
        diff = tm - set_time
    if debug :
        print("check_sunset(",lat,",",long,") ",diff.seconds," different");
    if ( diff.seconds < assert_seconds ) :
        return True;
    return False

# see if the difference between sunrise and the current time is within the proper range.
# this checks the calculations.
def check_sunrise(lat,long,tm) :
    lat_obs = Observer(lat,long)
    rise_time = sunrise(lat_obs,tm) 
    s="sun has already risen"
    if ( rise_time > tm) :
        diff=rise_time - tm
    else:
        s="sun is still set"
        diff= tm -rise_time
    if debug :
        print("check_sunrise (",lat,",",long,") ",diff.seconds," different");
    if ( diff.seconds < assert_seconds) :
        return True;
    return False


# calculate the radius around noon and anti-noon

lat_light = dict();
mixed=False;
# it's solar noon now, the sun might have rose yesterday and it might set tommorrow.
# for noon, the center of the sun is at it's highest point.  For sunrise, the leading edge of the sun is just over
#the horizon.  For sunset, the trailing edge of the sun is just over the top of the horizon.
# from sunrise to solar noon, the mid point of the sun has moved from the horizon to the noon point and the leading
#edge of the sun has moved from the horizion
# the sun will set when the mid point moves from the noon point to the horizon and the trailing edge of the sun moves 
# to the horizon.
# we have to calculate the values here because the sun won't be overhead at the same exact latitude for 24 hours.  it
# moves during that time.

light_points=[]
# we want to go from south_lat to north_lat but we want to be at a multiple of lat_incr, eg. if south_lat is -71 
# lat_incr is 20, we'd want to go from -60.

t=int((south_lat + lat_incr) / lat_incr)
south_lat=t*lat_incr
t=int((north_lat - lat_incr) / lat_incr)
north_lat=t*lat_incr

# we are trying to figure out where the sun is rising and setting now.
skipped_points=0
for lat in range( int(south_lat),int(north_lat) ,lat_incr) :
    lat_obs = Observer(lat,noon_long);
    found_points=0;
    try :
        # confirms the noon point.
        assert(check_noon(lat,noon_long,tm));
        # sunrise.
        rise_time = sunrise(lat_obs,tm);
        if ( rise_time > tm ) :
            rise_time = sunrise(lat_obs,yesterday);
        # how long has the day been so far
        so_far = (tm-rise_time).seconds
        # how many degrees has the sun moved so far
        so_far_deg = so_far * dps
        # set time.
        set_time = sunset(lat_obs,tm);
        if ( set_time > tm ) :
            set_time = sunset(lat_obs,tommorrow );
        # how long is left in the day.
        rem = (set_time - tm).seconds
        # how many degrees
        rem_deg = rem * dps

        # sunrise point
        rise_long = conv_long(noon_long-so_far_deg)
        # we do this +- 30 degrees to find a good value.
        l_rise_long=conv_long(rise_long-30);
        h_rise_long=conv_long(rise_long+30);
        (rise_long)=find_true_value(l_rise_long,h_rise_long,lat,tm,before_sunrise);
        # sunset point.
        set_long=conv_long(noon_long+rem_deg);
        l_set_long=conv_long(set_long-30);
        h_set_long=conv_long(set_long+30);
        (set_long) =find_true_value(l_set_long,h_set_long,lat,tm,after_sunset);

        # validate the calculations.
        if check_sunset(lat,set_long,tm) :
            light_points.append((lat,set_long));
            found_points=1;
        else :
            skipped_points = skipped_points+1;
            if debug :
                print("Sunset point skipped",(lat,set_long))
        if check_sunrise(lat,rise_long,tm) :
            light_points.append((lat,rise_long));
            found_points=2;
        else :
            skipped_points = skipped_points+1;
            if debug :
                print("Sunrise point skipped",(lat,rise_long))
        mixed=True;

    except ValueError as e :

        if ( debug ) :
            print("Unexpected Exception",lat,noon_long,e.args[0]);
        # how many points have we added?  if it's less than 2, we must have skipped some.
        skipped_points = skipped_points + (2-found_points);

# we want the points of the circle. dark_points are the start of darkness, light points are the start of light.
# how to handle dark or light at the poles.
# we have to add 180 to long and set the point at that point.
# its dark at 70 deg N lat.  from the point of view of the noon_point, the dark starts here.
# from the point of view of the anti_noon_point, the light starts
rad_data=[]
if ( southern_light_point != None ) :
    light_points.append(southern_light_point);

if ( northern_light_point != None ) :
    light_points.append(northern_light_point);

for i in light_points :
    if ( report_spherical ) :
        lr=great_circle(noon_point,i).kilometers;
        dr=great_circle(anti_noon_point,i).kilometers;
        sphere_circ=2*(lr+dr)
    else :
        lr=None
        dr=None
        sphere_circ=None


    if report_geodesic :
        glr=geodesic(noon_point,i).kilometers;
        gdr=geodesic(anti_noon_point,i).kilometers;
        geodesic_circ=2*(glr+gdr)
    else :
        glr=None
        gdr=None
        geodesic_circ=None

    # for lat,long, round to 2 decimal places.
    lat=round(i[0],2);
    long=round(i[1],2)
    rad_data.append([(lat,long),lr,dr,sphere_circ,glr,gdr,geodesic_circ])

print("Time is ", datetime.datetime.strftime(tm, "%m-%d-%Y %H:%M"))
print("Noon Point is      "+"("+f"{noon_lat:.{dec_point}f}"+"," +  f"{noon_long:.{dec_point}f}" + ") ");
print("Anti Noon Point is "+"("+f"{anti_noon_lat:.{dec_point}f}"+"," +  f"{anti_noon_long:.{dec_point}f}" + ") ");

if ( debug ) :
    for i in rad_data :
        print(i);
# put this into pandas data frame so we can use pandas analysis.
earth_data_frame = pd.DataFrame(data=rad_data,columns=["point","light_radius","dark_radius","circum","glight_radius","gdark_radius","gcircum"]);

# short cut for using a table.
results=[]
def get_data(name,df) :
    ret_list = [];
    ret_list.append(name);
    ret_list.append(df.mean());
    ret_list.append(df.max()-df.min());
    ret_list.append(df.std());
    return ret_list

if report_spherical :
    t=get_data("daylight radius (sphere)",earth_data_frame["light_radius"]);
    results.append(t);
    t=get_data("darkness radius (sphere)",earth_data_frame["dark_radius"]);
    results.append(t);
    t=get_data("circumference (great circle)",earth_data_frame["circum"]);
    results.append(t);
if report_geodesic :
    t=get_data("daylight_radius (actual)",earth_data_frame["glight_radius"]);
    results.append(t);
    t=get_data("darkness radius (actual)",earth_data_frame["gdark_radius"]);
    results.append(t);

tbl=tabulate.tabulate(results,headers=["value","average","range","std dev"],floatfmt="."+str(dec_point)+"f");
print(tbl)

# print the sunrise,sunset points.  From this data, one could validate the results.
if ( verbose ) :
    # light and dark points
    if report_geodesic :
        print("Radius Data Oblate Spheroid");
        tbl1=[];
        for i in rad_data:
            tbl1.append([i[0],i[4],i[5]]);
        tbl1_str=tabulate.tabulate(tbl1,headers=["point","distance from noon (km)","distance from anti-noon (km)"],floatfmt="."+ str(dec_point) + "f")
        print(tbl1_str)

    if report_spherical:
        print("Radius Data (Spherical");
        tbl1=[];
        for i in rad_data:
            tbl1.append([i[0],i[1],i[2]]);
        tbl1_str=tabulate.tabulate(tbl1,headers=["point","distance from noon (km)","distance from anti-noon (km)"],floatfmt="."+ str(dec_point) + "f")
        print(tbl1_str)

# report how many points were skipped.
# this give some idea of how good the calculation were.
if (skipped_points != 0 ) :
    print(str(skipped_points)+ " points were skipped");
