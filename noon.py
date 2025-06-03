from astral.sun import sunrise,sunset,zenith
from astral import Observer
from astral.sun import zenith,noon 
import datetime
import sys
import pytz

utc=pytz.UTC

if len(sys.argv) == 2:
    tm= datetime.datetime.strptime(sys.argv[1], "%m-%d-%Y %H:%M")
    tm=tm.astimezone(utc)
else:
    tm=datetime.datetime.now(tz=utc);

obs_lat=0
obs_long=0
obs=Observer(obs_lat,obs_long);
noon_tm=noon(obs,tm,tzinfo=utc);
dpm=15/60
# noon has either passed or is coming, so we can tell where it is.
if ( noon_tm > tm ) :
    # noon is coming.
    noon_time=(noon_tm - tm).seconds/60
    noon_long=obs_long + noon_time * dpm
else :
    noon_time=(tm - noon_tm).seconds/60
    noon_long=obs_long - noon_time * dpm

north_lat=23.5
south_lat = -23.5
north_obs= Observer(north_lat,noon_long);
south_obs= Observer(south_lat,noon_long);
north_zenith=zenith(north_obs,tm);
south_zenith=zenith(south_obs,tm);


done=False
first=True
while not done :
    if north_zenith == south_zenith :
        noon_lat = (north_lat + south_lat) /2
        done=True

    # are we close enough to stop?
    diff = abs(abs(north_lat) - abs(south_lat))

    if (not first and diff < .1 ) :
        noon_lat = north_lat
        done=True
    first=False;
    if ( north_zenith < south_zenith ) :
        # between center and south.
        south_lat = ( north_lat + south_lat)/2
        south_obs= Observer(south_lat,noon_long);
        south_zenith=zenith(south_obs,tm);
    else :
        north_lat = ( north_lat + south_lat)/2
        north_obs= Observer(north_lat,noon_long);
        north_zenith=zenith(north_obs,tm);

noon_obs=Observer(noon_lat,noon_long);

print(noon_lat, noon_long);
# antipode_lat 
antipode_lat= -1 * noon_lat
if ( noon_long < 0 ) :
    anti_long=noon_long + 180;
else:
    anti_noon_long=noon_long - 180;
print(antipode_lat, anti_long);


