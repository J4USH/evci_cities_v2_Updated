# AUTOGENERATED! DO NOT EDIT! File to edit: ../03_analysis.ipynb.

# %% auto 0
__all__ = ['run_episode', 'analyze_sites']

# %% ../03_analysis.ipynb 4
import re,copy
import numpy as np
import pandas as pd
import geopandas as gpd

import shapely
from fastapi import HTTPException
from fastapi.responses import JSONResponse
import os,json
from tqdm import tqdm
import mysql.connector
import matplotlib.pyplot as plt

from scipy.cluster.vq import kmeans2, whiten
from scipy.cluster.hierarchy import dendrogram, linkage
from scipy.cluster.hierarchy import fcluster

from .config import *
from .model import *

import warnings
warnings.filterwarnings("ignore")
idSelects=0
createdBy=0


# %% ../03_analysis.ipynb 5
def run_episode(charging_type,r,ui_inputs,s_df,txt,OUTPUT_PATH,urban_area,request_id,report={},cluster_th=0,cluster=False):

    mydb = mysql.connector.connect(
        host="139.59.23.75",
        port=5782,
        user="dbadminusr",
        password="$D3vel0per2024",
        database="EVCI"
    )
    mycursor = mydb.cursor()

    "This function runs a full episode of analysis on a set of sites."
    
    print('\n' + txt.capitalize() + ' Analysis')
    print('________________\n')
    total = r['total']
    
    #s_df = s_df[s_df['year 1'] == 1]
    #s_df = s_df.reset_index(drop=True)
    
    Nc = s_df.shape[0]
    print(f'Number of sites: {Nc}/{total}')

    #@title Compute scores

    backoff_factor = ui_inputs['backoff_factor']

    u_df = run_analysis(charging_type,r,s_df,backoff_factor=backoff_factor,sid=urban_area,aid=request_id,cluster=cluster,stage=txt)

    print(f'Total capex charges = INR Cr {sum(u_df.capex)/1e7:.2f}')
    print(f'Total opex charges = INR Cr {sum(u_df.opex)/1e7:.2f}')
    print(f'Total Margin = INR Cr {sum(u_df.margin)/1e7:.2f}')        

    report["no_site"]=f'{Nc}/{total}'
    report["capex"]=f'{sum(u_df.capex)/1e7:.2f}'
    report["opex"]=f'{sum(u_df.opex)/1e7:.2f}'
    report["margin"]=f'{sum(u_df.margin)/1e7:.2f}'
    
    #@title Prepare data
    s_u_df = s_df.copy()

    s_u_df['utilization'] = u_df.utilization
    s_u_df['unserviced'] = u_df.unserviced
    s_u_df['capex'] = u_df.capex
    s_u_df['opex'] = u_df.opex
    s_u_df['margin'] = u_df.margin
    s_u_df['max vehicles'] = u_df['max vehicles']
    s_u_df['estimated vehicles'] = u_df['estimated vehicles']

    #@title Save initial analysis to Excel
    output_df = s_u_df.copy()
    output_df.drop('geometry', axis=1, inplace=True)
    
    # Save output dataframe as both xlsx and json
    output_df.to_excel(OUTPUT_PATH + '/' + txt + '_' + charging_type + '_evci_analysis.xlsx')
    output_df.to_json(OUTPUT_PATH + '/' + txt + '_' + charging_type + '_evci_analysis.json', orient='records')
    
    confirmed_sites = s_u_df[s_u_df.utilization > cluster_th]
    print(f'confirmed sites with utilization > {int(cluster_th*100)}%: {confirmed_sites.shape[0]}')
    report['confirmed_utilization']=f'{int(cluster_th*100)}%: {confirmed_sites.shape[0]}'
    print(report)

    insert_query = """
INSERT INTO analysis_response_report (
    numberOfSite, capex, opex, margin, confirmedUtilization, 
    analysisInput_ID, output_for, createdBy
) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
"""
    values = (
    report['no_site'], report['capex'], report['opex'], report['margin'], 
    report['confirmed_utilization'], idSelects, (txt+"_"+charging_type), createdBy
)
    mycursor.execute(insert_query, values)
    mydb.commit()
    mycursor.close()
    mydb.close()
        
    return s_u_df, report

# %% ../03_analysis.ipynb 7
def analyze_sites(request_id,urban_area:str, ui_inputs,idSelect,db_inputs):
    "The function analyzes sites specified as part of a corridor."
    print(ui_inputs['cluster_th'])
    global idSelects
    global createdBy

    idSelects=idSelect
    createdBy=db_inputs['createdBy']


    try:
        main_res={}
        report={}
        
        #@title Read data from excel sheets
        print("Reading input files...", end="")
        model,site,traffic,grid,parking, INPUT_PATH, OUTPUT_PATH = setup_and_read_data(urban_area, request_id=request_id)
        print("done.")

        return_analysis = {}

        #set variables for clustering etc from the UI
        cluster = ui_inputs['cluster']
        cluster_th = ui_inputs['cluster_th']
        plot_dendrogram = ui_inputs['plot_dendrogram']

        #check if mandatory worksheets in xlsx files are available
        avail = data_availability_check(model,site,traffic,grid,parking)

        #check if any missingness
        missing = data_integrity_check(model,site,traffic,grid,parking)
        
        #@title Read required data sheets only
        #df = gpd.read_file(INPUT_PATH + '/shape_files/' + urban_area + '.shp')

        for charging_type in ['opportunity_charging','destination_charging']:
            print('\n' + charging_type.capitalize() + ' Analysis')

            #read global variables here
            r = read_globals(model,site,traffic,grid,parking,charging_type,ui_inputs)
            tr_data = get_grid_data(site,grid)

            r['di'] = tr_data['Transformer distance']

            df_t = site['sites']
            r['total'] = df_t.shape[0]
            data = df_t[df_t['Site category']==r['scenario_code']]
            data['Name'] = data['Name']
            data['Latitude'] = pd.to_numeric(data['Latitude'])
            data['Longitude'] = pd.to_numeric(data['Longitude'])
            data['geometry'] = [shapely.geometry.Point(xy) for xy in 
                                zip(data['Longitude'], data['Latitude'])]

            data_df = {}

            data_df = gpd.GeoDataFrame(data, geometry=data['geometry'])
            data_df = data_df.reset_index(drop=True)
            bb = data_df.total_bounds
            
            s_df = pd.DataFrame(columns=['Name',
                                        'Latitude', 
                                        'Longitude',
                                        'Transformer name',
                                        'Transformer latitude',
                                        'Transformer longitude',
                                        'Transformer distance',
                                        'num_vehicles',
                                        'year 1',
                                        'kiosk hoarding',
                                        'hoarding margin',
                                        'geometry'])

            s_df = s_df.reset_index(drop=True)

            if charging_type == 'opportunity_charging':
                for i in range(data_df.shape[0]):
                    s_df.loc[i] = [
                    data_df.loc[i].Name, 
                    data_df.loc[i].Latitude, 
                    data_df.loc[i].Longitude,
                    tr_data.loc[i]['Transformer name'],
                    tr_data.loc[i]['Transformer latitude'],
                    tr_data.loc[i]['Transformer longitude'],
                    tr_data.loc[i]['Transformer distance'],
                    data_df.loc[i]['Peak opportunity charging traffic'],
                    data_df.loc[i]['Year for site recommendation'],
                    data_df.loc[i]['Hoarding/Kiosk (1 is yes & 0 is no)'],
                    data_df.loc[i]['Hoarding margin'],
                    data_df.loc[i].geometry
                    ] 
            else:
                for i in range(data_df.shape[0]):
                    s_df.loc[i] = [
                    data_df.loc[i].Name, 
                    data_df.loc[i].Latitude, 
                    data_df.loc[i].Longitude, 
                    tr_data.loc[i]['Transformer name'],
                    tr_data.loc[i]['Transformer latitude'],
                    tr_data.loc[i]['Transformer longitude'],
                    tr_data.loc[i]['Transformer distance'],                    
                    data_df.loc[i]['Parking lot size'],
                    data_df.loc[i]['Year for site recommendation'],
                    data_df.loc[i]['Hoarding/Kiosk (1 is yes & 0 is no)'],
                    data_df.loc[i]['Hoarding margin'],
                    data_df.loc[i].geometry
                    ] 

            s_u_df, report_init = run_episode(charging_type,r,ui_inputs,s_df,'initial',OUTPUT_PATH,urban_area,request_id,report,cluster_th=cluster_th,cluster=cluster)
            main_res['initial_{}_df'.format(charging_type)]=json.loads(s_u_df.to_json(orient='records',default_handler=str))
            # main_res['initial_utilization_hist']=[float("{:.5f}".format(i)) for i in s_u_df['utilization'].tolist()]
            # main_res['initial_unserviced_hist']=[float("{:.5f}".format(i)) for i in s_u_df['unserviced'].tolist()]
            main_res['initial_{}_utilization_hist'.format(charging_type)]=[float("{:.5f}".format(i *100)) for i in s_u_df['utilization'].replace(np.nan,0).tolist()]
            main_res['initial_{}_unserviced_hist'.format(charging_type)]=[float("{:.5f}".format(i *100)) for i in s_u_df['unserviced'].replace(np.nan,0).tolist()]
            main_res['initial_{}_utilization_hist_max'.format(charging_type)]=float("{:.1f}".format(round((s_u_df['utilization'].replace(np.nan,0).max()*100)+10)))
            main_res['initial_{}_unserviced_hist_max'.format(charging_type)]=float("{:.1f}".format(round((s_u_df['unserviced'].replace(np.nan,0).max()*100)+10)))
            bb_box=bb.tolist()
            BB_json={
                "nw": {"lat": bb_box[1],"lng": bb_box[0]},
                "se": {"lat":bb_box[3],"lng":bb_box[2]}
            }
            main_res["map_bound_box_{}".format(charging_type)]=BB_json
            main_res['initial_{}_analysis'.format(charging_type)]=copy.copy(report_init)

            return_analysis[charging_type]={}
            return_analysis[charging_type]['initial']=s_u_df

            #@title Threshold and cluster
            clustering_candidates = s_u_df[s_u_df.utilization <= cluster_th]
            print(cluster)
            print(clustering_candidates.shape[0])
            if cluster and len(clustering_candidates) > 0:
                clusters = []
                print('candidates for clustering: ', clustering_candidates.shape[0])
                points = np.array((clustering_candidates.apply(lambda x: list([x['Latitude'], x['Longitude']]),axis=1)).tolist())
                print(points)
                
                if len(points)>1:
                    Z = linkage (points, method='complete', metric='euclidean');
                    if plot_dendrogram:
                        main_res['cluster_dendrogram']=Z.tolist()
                        plt.figure(figsize=(14,8))
                        dendrogram(Z);
                    max_d = 0.01
                    clusters = fcluster(Z, t=max_d, criterion='distance')
                    clustered_candidates = gpd.GeoDataFrame(clustering_candidates)
                    #base = grid_df.plot(color='none', alpha=0.2, edgecolor='black', figsize=(8,8))
                    #clustered_candidates.plot(ax=base, column=clusters, legend=True)
                else:
                    clustered_candidates = gpd.GeoDataFrame(clustering_candidates)

            #@title Build final list of sites
            confirmed_sites = s_u_df[s_u_df.utilization > cluster_th]
            print(f'confirmed sites with utilization > {int(cluster_th*100)}%: {confirmed_sites.shape[0]}')
            
            if cluster and len(clustering_candidates) > 0:
                val, ind = np.unique (clusters, return_index=True)
                clustered_sites = clustered_candidates.reset_index(drop=True)
                clustered_sites = clustered_sites.iloc[clustered_sites.index.isin(ind)]
                final_list_of_sites = pd.concat([confirmed_sites, clustered_sites], axis=0)

                print('final list: ', final_list_of_sites.shape[0])
                s_df = final_list_of_sites.copy()
                s_df = s_df.reset_index(drop=True)
                
                s_u_df, report_clust = run_episode(charging_type,r,ui_inputs,s_df,'cluster',OUTPUT_PATH,urban_area,request_id,report,cluster_th=cluster_th,cluster=cluster)
                return_analysis[charging_type]['cluster']=s_u_df
                main_res['cluster_{}_df'.format(charging_type)]=json.loads(s_u_df.to_json(orient='records',default_handler=str))
                # main_res['cluster_utilization_hist']=[float("{:.5f}".format(i)) for i in s_u_df['utilization'].tolist()]
                # main_res['cluster_unserviced_hist']=[float("{:.5f}".format(i)) for i in s_u_df['unserviced'].tolist()]
                main_res['cluster_{}_utilization_hist'.format(charging_type)]=[float("{:.5f}".format(i*100)) for i in s_u_df['utilization'].replace(np.nan,0).tolist()]
                main_res['cluster_{}_unserviced_hist'.format(charging_type)]=[float("{:.5f}".format(i*100)) for i in s_u_df['unserviced'].replace(np.nan,0).tolist()]
                main_res['cluster_{}_utilization_hist_max'.format(charging_type)]=float("{:.1f}".format(round((s_u_df['utilization'].replace(np.nan,0).max()*100)+10)))
                main_res['cluster_{}_unserviced_hist_max'.format(charging_type)]=float("{:.1f}".format(round((s_u_df['unserviced'].replace(np.nan,0).max()*100)+10)))
                main_res['cluster_{}_analysis'.format(charging_type)]=report_clust
                return_analysis[charging_type]['cluster']=s_u_df
            else:
                final_list_of_sites = confirmed_sites.copy()
        return OUTPUT_PATH,INPUT_PATH,return_analysis
    except Exception as e:
        error_message=str(e)
        
        raise HTTPException(status_code=500, detail=error_message)
