import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QDateEdit, QTimeEdit, QPushButton,QDialog,QLineEdit,QDialogButtonBox,QMessageBox
)
from PyQt5.QtCore import QDate, QTime, QDateTime,QTimeZone,QSettings
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import \
    NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import matplotlib.colors as mcolors
#import geopandas as gpd
from shapely.geometry import Polygon
from shapely.geometry import Point 
import missingno as msno
import os
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import matplotlib.patches as mpatches
import datetime
from zoneinfo import ZoneInfo
import pytz
from astral import Observer
from astral.sun import sunrise,sunset
from astral.sun import zenith
from enum import Enum
utc=pytz.UTC

# python script to visualize daylight on a projection of the globe earth imagined to be a flat earth map.
# the user can set various visualization elements via preferences and the day and time.

# what value is calculated for day and why.
class SunDataType(Enum) :
    DAY=1
    NIGHT=2
    DAY_24=3
    NIGHT_24=4
    NOT_SET=5 

# caches light data so we don't have to recacluate if we are just changing the visualization or the projection 
# point.
class PointSunlightData :
    def __init__(self,point):
        self.point=point
        self.day_type = SunDataType.NOT_SET;

    def set_data(self,day_type,sunrise=None,sunset=None):
        self.day_type=day_type;
        self.sunrise=sunrise
        self.sunset=sunset

    def to_string(self) :
        if self.day_type == SunDataType.NOT_SET :
            return;
        if self.day_type == SunDataType.NIGHT :
            day_light="NIGHT "
        elif self.day_type == SunDataType.NIGHT_24 :
            day_light="NIGHT (24 H)"
        elif self.day_type == SunDataType.DAY :
            day_light="DAY"
        else :
            day_light="DAY (24 HR)"

        # sometimes, sunrise is a date_time, sometimes a string.  That works, but.
        if self.sunrise == None :
            sunrise=""
        else :
            sunrise=str(self.sunrise);
        if self.sunset == None :
            sunset = ""
        else:
            sunset=str(self.sunset);


        return "Point (" + str(self.point.y) +  "," + str(self.point.x) + ")  " + day_light + " " + sunrise + " " + sunset;

# class we use to determine if we can use the cache.
class LastRunPrefs :
    def __init__(self ) :
        self.date_time = None
        self.proj_lat=0;
        self.proj_long=0;
        self.long_incr=0;
        self.lat_incr=0;


# we can use the cache if the date doesn't change and the increment for lat/long is not changed.
# techincally, if just the increments changed, we could re-use some of the cache, but I'm not sure it's
# worth it.
    def set_data(self,date_time) :
        changed=False;
        if self.date_time == None :
            changed=True;
        else :
            if self.date_time != date_time :
                changed=True;
        self.date_time=date_time;
        settings = QSettings("MyCompany", "MyApp")
        lat_deg= settings.value("lat_deg", 10, type=float)
        long_deg = settings.value("long_deg", 10, type=float)
        if self.lat_incr != lat_deg or self.long_incr != long_deg :
            change=d=True;
        self.lat_incr=lat_deg
        self.long_incr=long_deg
        return changed


# information about day and night points on the globe.
# noon_point is the point we found that had the lowest zenith at the time.  This is not the global solar noon
# but the best we have at first glance.
class WorldSunData :
    def __init__(self) :
        self.lowest_zenith=90;
        self.noon_point=None
        self.point_list=[];
        self.date_time = None
        self.mk_point_list();

    # the list of points to check for daylight.
    def mk_point_list(self) :
        self.point_list=[];
        # potentially reduce density at 80N.
        settings = QSettings("MyCompany", "MyApp")
        lat_incr= settings.value("lat_deg", 10, type=int)
        long_incr = settings.value("long_deg", 10, type=int)
        # note that we have a lot of points at the north pole because the project gets very dense.  This
        # lessens the density.  We could also adjust alpha or point sizes.  This method is quick, and maybe
       # doesn't work that well.
        polar_incr=5
        polar_start=80

        lat_list = list(range(-90,90+lat_incr-1,lat_incr) )
        # special latitdues include the artic circles and the tropics
        lat_list.extend([-66.36,-23.5,23.5, 66.36 ]);
        for lat in lat_list :
            if (lat == 90 ) :
                    self.point_list.append(WorldSunData.mk_Point(90,0));
            else :
                if ( lat < 90 and lat > polar_start ) :
                    for long in range(-180,180+polar_incr-1,polar_incr) :
                        self.point_list.append(WorldSunData.mk_Point(lat,long));
                else :
                    for long in range(-180,180+long_incr-1 ,long_incr) :
                        self.point_list.append(WorldSunData.mk_Point(lat,long))


    # check if it's daylight at a point.
    def is_day(self,p,d) :
        obs=Observer(p.point.y,p.point.x);
        d=d.replace(tzinfo=utc);
        if p.day_type != SunDataType.NOT_SET :
            if p.day_type == SunDataType.DAY_24 or p.day_type == SunDataType.DAY :
                return True;
            else :
                return False;
    
        try :
            # solar noon can only be between the tropics so don't bother to check elsewhere.
            if ( abs(p.point.y) < 24 ) :
                z=zenith(obs,dateandtime=d)
                if ( z < self.lowest_zenith) :
                    self.lowest_zenith=z
                    self.noon_point = p.point
            try :
                rise_time =  sunrise(obs,d ).replace(tzinfo=utc)
                set_time =  sunset(obs,d ).replace(tzinfo=utc)
            except ValueError as e:
                if "above" in e.args[0] :
                    p.set_data(SunDataType.DAY_24);
                    return(True);
                else : 
                    p.set_data(SunDataType.NIGHT_24);
                    return(False);
                
            if ( rise_time > set_time ) :
                # daylight from sunrise to midnight
                # light from midnight to sunset.
                # dark from sunset to sunrise,
                # light from sunrise to midnight.
                if ( d > rise_time ) :
                    # after sunrise
                    p.set_data(SunDataType.DAY,rise_time,set_time);
                    return True;
                else :
                    if ( d < set_time )  :
                        # LIGHT before sunset
                        p.set_data(SunDataType.DAY,rise_time,set_time);
                        return True;
                    else :
                        # DARK after sunset
                        p.set_data(SunDataType.NIGHT,rise_time,set_time);
                        return False ;
            if ( d > rise_time and d < set_time) :
                # BETWEEN sunrise and sunset
                p.set_data(SunDataType.DAY,rise_time,set_time);
                return True
            else :
                # sun hasn't written or hasn't set
                p.set_data(SunDataType.NIGHT,rise_time,set_time);
                return False 
        except ValueError as e:
            return True
    
    def mk_Point(lat,long) :
        return PointSunlightData(Point(long,lat))

class PreferencesDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Preferences")
        print("HERE");
        
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("How far between Latitude lines to Plot:"))
        self.lat_degrees=QLineEdit(self);
        layout.addWidget(self.lat_degrees)
        layout.addWidget(QLabel("How far between Longitude lines to Plot:"))
        self.long_degrees=QLineEdit(self);
        layout.addWidget(self.long_degrees)
        layout.addWidget(QLabel("Size of point to plot:"))
        self.point_size=QLineEdit(self);
        layout.addWidget(self.point_size)
        layout.addWidget(QLabel("Alpha of the point:"))
        self.alpha=QLineEdit(self);
        layout.addWidget(self.alpha)
        layout.addWidget(QLabel("lattitude of projection:"))
        self.proj_lat=QLineEdit(self);
        layout.addWidget(self.proj_lat)
        layout.addWidget(QLabel("longitude of projection:"))
        self.proj_long=QLineEdit(self);
        layout.addWidget(self.proj_long)

        # Load saved value
        settings = QSettings("MyCompany", "MyApp")
        self.alpha.setText( settings.value("alpha", 10, type=str))
        self.lat_degrees.setText( settings.value("lat_deg", 10, type=str))
        self.long_degrees.setText( settings.value("long_deg", 10, type=str))
        self.point_size.setText(settings.value("point_size", 10, type=str))
        self.proj_long.setText(settings.value("proj_long", 10, type=str))
        self.proj_lat.setText(settings.value("proj_lat", 10, type=str))

        
        buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)
        layout.addWidget(buttonBox)
        print("DONE");
    
    def accept(self):
        # Save value
        settings = QSettings("MyCompany", "MyApp")
        # values here must be floats and must be within a set value.  We need to check each one so
        # we can set what we can.
        print("HERE");
        settings.setValue("Error", "");
        settings.remove("Error");
        try :
            lat_val=float(self.lat_degrees.text());
            settings.setValue("lat_deg", self.lat_degrees.text())
        except ValueError:
            print("lat val",self.lat_degrees.text()," is not floating point.  Ignored");
            settings.setValue("Error","value is not a float");

        try :
            long_val=float(self.long_degrees.text());
            settings.setValue("long_deg", self.long_degrees.text())
        except ValueError:
            print("long val",self.lat_degrees.text()," is not floating point.  Ignored");
            settings.setValue("Error","value is not a float");

        try :
            point_size=float(self.point_size.text());
            settings.setValue("point_size", self.point_size.text())
        except ValueError:
            print("point_size ",self.point_size.text()," is not floating point.  Ignored");
            settings.setValue("Error","value is not a float");

        try :
            alpha=float(self.alpha.text());
            settings.setValue("alpha", self.alpha.text())
        except ValueError:
            print("alpha",self.alpha.text()," is not floating point.  Ignored");
            settings.setValue("Error","value is not a float");

        try :
            proj_lat=float(self.proj_lat.text());
            if (proj_lat >= -90 and proj_lat <=90 ) :
                settings.setValue("proj_lat", self.proj_lat.text())
        except ValueError:
            print("proj_lat",self.proj_lat.text()," is not floating point.  Ignored");
            settings.setValue("Error","value is not a float");

        try :
            proj_long=float(self.proj_long.text());
            if (proj_long >= -180 and proj_long <=180 ) :
                settings.setValue("proj_long", self.proj_long.text())
        except ValueError:
            print("proj_long",self.proj_long.text()," is not floating point.  Ignored");
            settings.setValue("Error","value is not a float");
        super().accept()

class DateTimePlotApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sunshine visualizor on Gleason-like Map")
        self.resize(600, 500)
        self.worldData = WorldSunData();

        main_layout = QVBoxLayout()

        # Top layout for date and time inputs
        input_layout = QHBoxLayout()

        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())

        self.time_edit = QTimeEdit()
        current_time= QDateTime.currentDateTime();
        self.time_edit.setTime(current_time.time());
        self.time_edit.setDisplayFormat("HH:mm:ss")

        self.plot_button = QPushButton("Plot Data")
        self.plot_button.clicked.connect(self.update_plot)

        self.pref_button = QPushButton("preferences")

        self.pref_button.clicked.connect(self.show_preferences)

        self.label = QLabel("Selected datetime:")

        self.proj = ccrs.AzimuthalEquidistant(central_latitude=90, central_longitude=0)
        self.last_run = LastRunPrefs();

        input_layout.addWidget(QLabel("Date:"))
        input_layout.addWidget(self.date_edit)
        input_layout.addWidget(QLabel("Time:"))
        input_layout.addWidget(self.time_edit)
        input_layout.addWidget(self.plot_button)
        input_layout.addWidget(self.pref_button)

        main_layout.addLayout(input_layout)
        main_layout.addWidget(self.label)

        # Matplotlib figure
        #self.figure = Figure(figsize=(10, 10))
        self.figure = plt.figure(figsize=(10, 10))
        self.canvas = FigureCanvas(self.figure)
        main_layout.addWidget(self.canvas)
        main_layout.addWidget(NavigationToolbar(self.canvas, self))
        main_layout.addWidget(self.canvas)
        self.setLayout(main_layout)
        #self.update_plot()

    def show_preferences(self):
        dlg = PreferencesDialog(self)
        # updates are made to settings
        # it would be better to make a note here is values are invalid.  We just ignore it now.
        dlg.exec_()
        # check for errors.
        settings = QSettings("MyCompany", "MyApp")
        err=settings.value("Error");
        if err != "" :
            dlg2 = QMessageBox(self)
            dlg2.setWindowTitle("Error ");
            dlg2.setText("Non float values in prefereces are ignored");
            dlg2.exec()


    def update_plot(self):
        date = self.date_edit.date()
        time = self.time_edit.time()
        date_time = QDateTime(date, time)
        date_time_utc = date_time.toUTC();
        time_string = date_time_utc.toString('yyyy-MM-dd HH:mm:ss')
        suf=date_time.toString('yyyy_MM_dd_HH_mm');
        dt=date_time_utc.toPyDateTime();
        self.label.setText(time_string + " UTC");
        self.show_map(dt,suf);

    # this is separated just to allow for drawing multiple pictures.  This is not implemented.
    def show_map(self,dt,suf) :
        self.figure.clear()
        settings = QSettings("MyCompany", "MyApp")
        marker_size= settings.value("point_size", 10, type=int)
        point_alpha= settings.value("alpha", 10, type=float)
        proj_lat= settings.value("proj_lat", 10, type=float)
        proj_long= settings.value("proj_long", 10, type=float)

        db_str = os.environ.get("DEBUG","0");
        debug=int(db_str);
        self.proj = ccrs.AzimuthalEquidistant(central_latitude=proj_lat, central_longitude=proj_long)
        self.ax = plt.axes(projection=self.proj)
        #self.figure, self.ax = plt.subplots(1,1,subplot_kw={'projection':self.proj})
        self.ax.set_global()
        self.ax.coastlines()
        self.ax.gridlines(draw_labels=True, linewidth=0.5, color='gray', alpha=0.5)

        # 3. Optional: Add countries
        self.ax.add_feature(cfeature.BORDERS, linewidth=0.5)
        self.ax.add_feature(cfeature.LAND, facecolor='lightgray')
        self.ax.add_feature(cfeature.OCEAN, facecolor='lightblue')

        changed=self.last_run.set_data(dt ) 
        if changed :
            self.worldData.noon_point=None
            self.worldData.lowest_zenith = 90
            self.worldData.mk_point_list();
        for p in self.worldData.point_list :
            if self.worldData.is_day(p,dt) :
                color="yellow"
            else :
                color="black"
            self.ax.plot(p.point.x,p.point.y,'o', markersize=marker_size, transform=ccrs.PlateCarree(),color=color,alpha=point_alpha)
        self.ax.plot(self.worldData.noon_point.x,self.worldData.noon_point.y,'o', markersize=5, transform=ccrs.PlateCarree(),color='orange');
        if changed :
            if ( debug > 1 ) :
                for p in self.worldData.point_list :
                    print(p.to_string());
        if debug > 0 :
            print("Noon point",self.worldData.noon_point);
        self.canvas.draw()
        plt.savefig(os.getcwd()+'/map_'+suf +'.jpg',dpi=400, bbox_inches="tight")

if __name__ == "__main__":
    # initialize default values.
    settings = QSettings("MyCompany", "MyApp")
    settings.setValue("lat_deg", "1");
    settings.setValue("long_deg", "1")
    settings.setValue("point_size","1")
    settings.setValue("alpha", ".01");
    settings.setValue("proj_long", "0");
    settings.setValue("proj_lat", "90");
    settings.setValue("Error", "");
    app = QApplication(sys.argv)
    window = DateTimePlotApp()
    window.show()
    sys.exit(app.exec_())

