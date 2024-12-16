# AUTOGENERATED! DO NOT EDIT! File to edit: ../00_config.ipynb.

# %% auto 0
__all__ = ['check_files_availability', 'setup_and_read_data', 'data_availability_check', 'data_integrity_check',
           'data_missing_check', 'get_category', 'get_grid_data', 'read_globals']

# %% ../00_config.ipynb 5
import os
import numpy as np
import pandas as pd
import json
from fastapi import HTTPException
import geopandas as gpd
import shapely

import warnings
warnings.filterwarnings("ignore")

def check_files_availability(urban_area:str, input_path="../../../media/evci/uploads/dataManagement/"):
    "This function simply checks if all the required input files mentioned above are available."

    INPUT_PATH = input_path + urban_area + '/'

    files_not_found = []

    if not os.path.exists(input_path + 'modelCity.xlsx'): files_not_found.append('modelCity.xlsx')
    if not os.path.exists(INPUT_PATH + 'Sites.xlsx'): files_not_found.append('sites.xlsx')
    if not os.path.exists(INPUT_PATH + 'Traffic.xlsx'): files_not_found.append('traffic.xlsx')
    if not os.path.exists(INPUT_PATH + 'Grid.xlsx'): files_not_found.append('grid.xlsx')
    if not os.path.exists(INPUT_PATH + 'Parking.xlsx'): files_not_found.append('parking.xlsx')
    
    return files_not_found

# %% ../00_config.ipynb 7
def setup_and_read_data(urban_area:str, input_path="../../../media/evci/uploads/dataManagement/", output_path="../../../media/evci/uploads/dataManagement/", request_id=""):
    "This function sets up paths and reads input excel files for a specified corridor"

    INPUT_PATH = input_path + urban_area + '/'
    
    OUTPUT_PATH = output_path + '/' + urban_area +'/' + request_id + '/'
    print(OUTPUT_PATH)
    
	
    if not os.path.exists(OUTPUT_PATH):
       try:
           os.makedirs(OUTPUT_PATH, exist_ok=True)
           print(f"Directory created successfully: {OUTPUT_PATH}")
       except Exception as e:
          print(f"Failed to create directory: {e}")

          
    try:
        model   = pd.read_excel(input_path + "modelCity.xlsx", sheet_name=None)
        sites   = pd.read_excel(INPUT_PATH + "Sites.xlsx", sheet_name=None) 
        traffic = pd.read_excel(INPUT_PATH + "Traffic.xlsx", sheet_name=None, header=None)
        grid    = pd.read_excel(INPUT_PATH + "Grid.xlsx", sheet_name=None)
        parking = pd.read_excel(INPUT_PATH + "Parking.xlsx", sheet_name=None, header=None)
    except Exception as e:
        error_message="error in call setup_and_read_data(): "+str(e)
        raise HTTPException(status_code=500, detail=error_message)
    
    return model, sites, traffic, grid, parking, INPUT_PATH, OUTPUT_PATH

# %% ../00_config.ipynb 12
def data_availability_check(m,s,t,g,p): 
    "This function checks if the excel files contain the mandatory worksheets."
    
    model_sheets = set(['planning_scenarios','charger_details','chargers_site_categories',
                            'chargers_opportunity_charging', 'battery_specific', 'others'])
    df = s['sites']['Opportunity charging traffic profile']
    traffic_sheets = set(df[df != 0].unique())             
    grid_sheets = set(['grid'])
    parking_sheets = set(s['sites']['Site category'].unique())
    sites_sheets = set(['sites'])
    
    retval = []
    
    if not model_sheets.issubset(set(m.keys())): retval.append('model')
    if not sites_sheets.issubset(set(s.keys())): retval.append('sites')
    if not traffic_sheets.issubset(set(t.keys())): retval.append('traffic')
    if not grid_sheets.issubset(set(g.keys())): retval.append('grid')
    if not parking_sheets.issubset(set(p.keys())): retval.append('parking')
    
    return retval

# %% ../00_config.ipynb 16
def data_integrity_check(m,s,t,g,p, verbose=False):
    "This function checks for integrity of excel data by checking missing values."
    missing = []
    
    for x in [m,s,t,g,p]:
        tmpx = {}
        for k in x.keys():
            total = x[k].shape[0]
            tmpx[k] = []
            for c in x[k].columns:
                if sum(pd.isna(x[k][c])) > 0:
                    if verbose: 
                        print(f"Column '{c}' of '{k}' has {sum(pd.isna(x[k][c]))}/{total} missing values")
                    tmpx[k].append(c)
        missing.append(tmpx)
                    
    return missing

# %% ../00_config.ipynb 20
def data_missing_check(sid,file,input_path="../../../media/evci/uploads/dataManagement/"):
    """Function checks for missing values in the excel data"""
    try:
        path = input_path+sid+"/"+file
        columns_to_check=[]
        sheet=""
        if file=="Sites.xlsx": 
            sheet='sites'
            columns_to_check=["Name","Longitude","Latitude","type of site","Traffic congestion (4 if in city & 2 if on highway)",
            "Year for Site recommendation Hoarding/Kiosk (1 is yes & 0 is no)","Hoarding margin Kiosk margin Available area (in sqm)","Upfront cost per sqm (land)",
            "Yearly cost per sqm (land)","Upfront cost per sqm (kiosk)","Yearly cost per sqm (kiosk)","Upfront cost per sqm (hoarding)",
            "Yearly cost per sqm (hoarding)","Battery swap available (1 is yes and 0 is no)"]
        elif file=="Grid.xlsx":
            sheet='grid'
            columns_to_check=["Name of transformer","Address","Longitude","Latitude","Tariff","Power Outage","Available load"]
        elif file=="Traffic.xlsx":
            sheet='profile'
            columns_to_check=["Name","vehicles"]

        df=pd.read_excel(path,sheet_name=[sheet])
        tmpx = {}
        for k in df.keys():
            tmpx= []
            for c in df[k].columns:
                if c in columns_to_check:
                    if sum(pd.isna(df[k][c])) > 0:
                        tmpx.append(c)
        if len(tmpx)>0:return {"missing":True,"columns":tmpx}
        else:return {"missing":False}
    except Exception as e:
        error_message="Error in call data_missing_check(): "+str(e)
        raise HTTPException(status_code=500, detail=error_message)


# %% ../00_config.ipynb 22
def get_category(sid,input_path="../../../media/EVCI/uploads/dataManagement/"):
   """Function fetch site categories available in sites.xlsx file"""
   try:
    path=input_path+sid+"Sites.xlsx"
    cols="Site category"
    df=pd.read_excel(path,sheet_name=["sites"])
    unique_=df[cols].unique().to_list()
   except Exception as e:
    error_message="error in call get_category(): "+str(e)
    raise HTTPException(status_code=500, detail=error_message)

# %% ../00_config.ipynb 23
def get_grid_data(s,g):
    tr_lat = []
    tr_long = []
    tr_di = []
    tr_name = []
    
    try:
        if g['grid'].shape[0] == 0:
            di = [0]*s['sites'].shape[0]
            return di
        
        data = s['sites']
        data['geometry'] = [shapely.geometry.Point(xy) for xy in 
                            zip(data['Longitude'], data['Latitude'])]

        data_df = {}

        data_df = gpd.GeoDataFrame(data, geometry=data['geometry'])
        data_df = data_df.reset_index(drop=True)
        
        s_df = data.copy()
        s_df = s_df.reset_index(drop=True)
        s_df.geometry = data_df.geometry

        data = g['grid']
        data['geometry'] = [shapely.geometry.Point(xy) for xy in 
                            zip(data['Longitude'], data['Latitude'])]

        data_df = {}

        data_df = gpd.GeoDataFrame(data, geometry=data['geometry'])
        data_df = data_df.reset_index(drop=True)
        
        g_df = data.copy()
        g_df = g_df.reset_index(drop=True)
        g_df.geometry = data_df.geometry

        s_crs = gpd.GeoDataFrame(s_df, crs='EPSG:4326')
        s_crs = s_crs.to_crs('EPSG:5234')

        g_crs = gpd.GeoDataFrame(g_df, crs='EPSG:4326')
        g_crs = g_crs.to_crs('EPSG:5234')
        
        for i in range(s_df.shape[0]):
            distance_from_i = g_crs.geometry.distance(s_crs.geometry.loc[i])
            nearest_to_i = distance_from_i.idxmin()
            tr_lat.append(g_df.loc[nearest_to_i]['Latitude'])
            tr_long.append(g_df.loc[nearest_to_i]['Longitude'])
            tr_name.append(g_df.loc[nearest_to_i]['Name of transformer'])
            tr_di.append(distance_from_i[nearest_to_i]/1e3)
    except Exception as e:
        error_message="error in call read_grid_data()"+str(e)
        raise HTTPException(status_code=500, detail=error_message)
    
    s_df['Transformer name'] = tr_name
    s_df['Transformer longitude'] = tr_long
    s_df['Transformer latitude'] = tr_lat
    s_df['Transformer distance'] = tr_di

    return s_df

# %% ../00_config.ipynb 26
def read_globals(m,s,t,g,p,charging_type,ui_inputs):
  "This function returns all global parameters read from the xlsx."
  
  x = json.dumps(ui_inputs)
  ui_inputs = json.loads(x)

  r = {}

  df_p = m['planning_scenarios']
  df_c = m['charger_details']
  df_sc = m['chargers_site_categories']
  df_b = m['battery_specific']
  df_o = m['others']
  
  scenario_code = df_p[df_p['Site categories']==ui_inputs['planning_scenario']]['Scenario code'].iloc[0]

  # read all other parameters from the xlsx
  
  r['scenario_code']=scenario_code
  r['M'] = df_p[df_p['Site categories']==ui_inputs['planning_scenario']]['Charger types'].iloc[0].split(',')
  r['C'] = r['M']

  r['Kj'] = {}
  r['Dj'] = {}
  r['Hj'] = {}
  r['Qj'] = {}
  r['tj'] = {}
  r['Mj'] = {}
  r['Gk'] = {}
  r['Cij'] = {}

  for c in r['C']:
    df_t = df_c[df_c['Type of vehicle']==c]
    charger = df_t['Compatible charger'].iloc[0]
    if charging_type == 'opportunity_charging':
      r['Cij'][c] = [i*df_sc[(df_sc['Chargers']==charger) & (df_sc['Site categories']==ui_inputs['planning_scenario'])]['No. of chargers'].iloc[0] for i in s['sites']['No. of charger bundles opportunity charging']]
    else:
      r['Cij'][c] = [i*df_sc[(df_sc['Chargers']==charger) & (df_sc['Site categories']==ui_inputs['planning_scenario'])]['No. of chargers'].iloc[0] for i in s['sites']['No. of charger bundles destination charging']]
    r['Kj'][c] = int(df_t['Capex per charger'].iloc[0].split('-')[0])
    r['Dj'][c] = df_t['Charging power'].iloc[0]
    #r['Hj'][c] = df_t['Required space per charger'].iloc[0]
    r['Qj'][c] = df_t['Annual maintenance per charger'].iloc[0]
    if charging_type == "opportunity_charging":
      r['tj'][c] = df_t['Charging time for opportunity charging (hrs)'].iloc[0]
    else:
      r['tj'][c] = df_t['Charging time for destination charging (hrs)'].iloc[0]

  r['N'] = 500
  r['Ng'] = 0

  r['timeslots'] = {k: 24/v for k, v in r['tj'].items()}
  timeslots = r['timeslots']
  
  df_t = s['sites']
  r['Nc'] = df_t[df_t['Site category']==scenario_code].shape[0]
  Nc = r['Nc']

  r['Gi'] = [0]*Nc
  r['Ri'] = [0]*Nc
  r['Wi'] = [ui_inputs['cabling_cost']]*Nc
  r['Ai'] = [ui_inputs['Ai']]*Nc
  r['Li'] = [ui_inputs['Li']]*Nc
  r['Bi'] = [ui_inputs['Bipc'] * ui_inputs['Birate'] * 24 * 365]*Nc # e.g. 25% of Rs 3.5/KWh per year

  r['MH'] = [s['sites'].loc[i]['Hoarding margin'] for i in range(Nc)]
  r['MK'] = [s['sites'].loc[i]['Kiosk margin'] for i in range(Nc)]

  r['Eg'] = {k: [ui_inputs['Eg']] * int(v) for k, v in timeslots.items()}
  r['Er'] = {k: [0] * int(v) for k, v in timeslots.items()}
  r['Mg'] = {k: [ui_inputs['Eg'] * r['MK'][0]] * int(v) for k, v in timeslots.items()} # FIX THIS index 0 !!
  r['Mr'] = {k: [0] * int(v) for k, v in timeslots.items()}
  r['l']  = {k: [1] * int(v) for k, v in timeslots.items()}
    
  r['K'] = ui_inputs['years_of_analysis']
  r['charger_types'] = r['M']
  r['years_of_analysis'] = ui_inputs['years_of_analysis']
  r['capex_2W']  = ui_inputs['capex_2W']
  r['capex_3WS'] = ui_inputs['capex_3WS']
  r['capex_4WS'] = ui_inputs['capex_4WS']
  r['capex_4WF'] = ui_inputs['capex_4WF']
  r['hoarding_cost'] = 900000
  r['kiosk_cost'] = 180000
  r['year1_conversion'] = ui_inputs['year1_conversion']
  r['year2_conversion'] = ui_inputs['year2_conversion']
  r['year3_conversion'] = ui_inputs['year3_conversion']
  r['fast_charging'] = ui_inputs['fast_charging']
  r['slow_charging'] = ui_inputs['slow_charging']
  r['holiday_percentage'] = ui_inputs['holiday_percentage']
  
  # now lets derive all other parameters that depend on the UI inputs.
  r['CH'] = [r['hoarding_cost']]*Nc
  r['CK'] = [r['kiosk_cost']]*Nc
  r['pj'] = {1: r['year1_conversion'], 
        2: r['year2_conversion'], 
        3: r['year3_conversion']}

  r['Pj'] = max(r['pj'].values()) 

  #Traffic profile/ Parking profile
  # read hourly vehicular traffic from the traffic.xlsx or parking.xlsx depending on charging_type
  
  p_df = {'opportunity_charging': t, 'destination_charging': p}

  profiles = list(p_df[charging_type].keys())
  djworking = {}

  vehicle_type = {
    "2W": "2W",
    "3W": "3W",
    "4WS": "4W",
    "4WF": "4W",
    "Bus": "Bus",
  }

  for profile in profiles:
    avg_traffic = p_df[charging_type][profile].iloc[3:27,1].to_list()
    avg_traffic_per_type = {}
    for c in r['M']:
      tmp_df = p_df[charging_type][profile]
      frac = tmp_df[tmp_df[0]==vehicle_type[c]].iloc[0,1]
      avg_traffic_per_type[c] = [i*frac for i in avg_traffic]
      # stretch or compress here based on timeslots
      if r['timeslots'][c] > 24:
        scale = int(r['timeslots'][c]/24)
        avg_traffic_per_type[c] = [i for i in avg_traffic_per_type[c] for _ in range(scale)]
      else:
        scale = int(24/r['timeslots'][c])
        avg_traffic_per_type[c] = avg_traffic_per_type[c][::scale]
      djworking[c] = [np.round(i,2) for i in avg_traffic_per_type[c]]
    r['djworking'] = djworking

    djholiday = {}
    for profile in profiles:
      tmp_df = p_df[charging_type][profile]
      holiday_percentage = r['holiday_percentage'] = tmp_df[tmp_df[0]=='holiday_percentage'].iloc[0,1]
      for c in r['M']:
        djholiday[c] = [np.round(i*holiday_percentage,2) for i in djworking[c]]
    r['djholiday'] = djholiday
    
    for profile in profiles:
      tmp_df = p_df[charging_type][profile]
      fast_charging = tmp_df[tmp_df[0]=='fast_charging'].iloc[0,1]
      slow_charging = tmp_df[tmp_df[0]=='slow_charging'].iloc[0,1]
      r['qjworking'] = {}
      r['qjholiday'] = {}
      for c in r['M']:
        r['qjworking'][c] = [slow_charging + fast_charging] * int(timeslots[c])
        r['qjholiday'][c] = [slow_charging + fast_charging] * int(timeslots[c])
    
  return r
