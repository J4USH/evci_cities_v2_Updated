from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import mysql.connector
import logging
import traceback
from decimal import Decimal
from evci_tool.analysis import analyze_sites
import json
import os
import pandas as pd

app = FastAPI()

# Pydantic model to define input structure
class AnalyzeRequest(BaseModel):
    analysisInput_ID: int
    site_id:int

class ErrorResponseModel(BaseModel):
    message: str
    

# Default UI inputs



@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    print(traceback.format_exc())  # Get the stack trace as a string
    
    # Capture request details (e.g., method, URL)
    print(f"{request.method} {request.url}")

    
    error = str(exc.detail).replace("500:", "").strip()
    return JSONResponse(
        status_code=exc.status_code,
        content={"status": "error", "message": str(error)}
    )



@app.post("/analyze",responses={500: {"status":"error","model": ErrorResponseModel}})
async def analyze(request: AnalyzeRequest):
    idSelect = request.analysisInput_ID
    filename = request.site_id

    ui_inputs = { 
    "planning_scenario": "Public Places",
    "years_of_analysis": [1,2,3],
    "Ai": 50,
    "Li": 1500,
    "Bipc": .25,
    "Birate": 3.5,
    "Eg": 5.5,
    "backoff_factor":1,
    "cabling_cost": 500000,
    "capex_2W": 2500,
    "capex_3WS": 112000,
    "capex_4WS": 250000,
    "capex_4WF": 1500000,
    "hoarding cost": 900000,
    "kiosk_cost": 180000,
    "year1_conversion": 0.02,
    "year2_conversion": 0.05,
    "year3_conversion": 0.1,
    "holiday_percentage": 0.3,
    "fast_charging": 0.3,
    "slow_charging": 0.15,
    "cluster": True,
    "cluster_th": 0.04,
    "plot_dendrogram": True
}
    


    query = "SELECT * FROM analysis_inputs WHERE id = %s;"
    mydb = mysql.connector.connect(
        host="139.59.23.75",
        port=5782,
        user="dbadminusr",
        password="$D3vel0per2024",
        database="EVCI"
    )
    mycursor = mydb.cursor()
    mycursor.execute(query, (idSelect,))

    # Retrieve column names and data
    column_names = [i[0] for i in mycursor.description]
    results = [{**dict(zip(column_names, row))} for row in mycursor.fetchall()]

    if not results:
        mycursor.close()
        mydb.close()
        return {"status": "failure","message":"Please Give THE CORRECT ANALYSIS AND SITE ID!!!!!!!"}

    db_input = results[0]
    if db_input["holiday_percentage"]!=0 and db_input["holiday_percentage"] is not None:
        db_input["holiday_percentage"]/=100.0
    if db_input["fast_charging"]!=0 and db_input["fast_charging"] is not None:
        db_input["fast_charging"]/=100.0
    if db_input["slow_charging"]!=0 and db_input["slow_charging"] is not None:
        db_input["slow_charging"]/=100.0

    print(db_input)

    # Close database connection
    if db_input["years_of_analysis"]!=0 and db_input["years_of_analysis"] is not None:
        yoe=db_input["years_of_analysis"]
    else:
        yoe=3

    # Format db_input for compatibility
    for key, value in db_input.items():
        if isinstance(value, Decimal):
            db_input[key] = float(value)
        if key == "years_of_analysis":
            if db_input[key]!=0:
                if db_input[key]==1:
                    db_input[key]=[1,2]
                else:
                    db_input[key] = list(range(1, db_input[key]+1))

    
                
        

    # # Override defaults with database values if present
    for key in ui_inputs:
        if key in db_input:
            if db_input[key] is not None and db_input[key]!=0:
                ui_inputs[key] = db_input[key]
                
    
    
    if ui_inputs['cluster'] == 1:
        ui_inputs['cluster']=True
    if ui_inputs['cluster'] == 0:
        ui_inputs['cluster']=False


    # print(ui_inputs['cluster'])
    if(db_input['capex_2w_charger'] is not None and db_input['capex_2w_charger']!=0):
        ui_inputs['capex_2W']=db_input['capex_2w_charger']
    if(db_input['capex_3w_charger'] is not None and db_input['capex_3w_charger']!=0):
        ui_inputs['capex_3WS']=db_input['capex_3w_charger']
    if(db_input['capex_4w_charger'] is not None and db_input['capex_4w_charger']!=0):
        ui_inputs['capex_4WS']=db_input['capex_4w_charger']
    if(db_input['capex_4wf_charger'] is not None and db_input['capex_4wf_charger']!=0):
        ui_inputs['capex_4WF']=db_input['capex_4wf_charger']
    if(db_input['hoarding_capex_cost'] is not None and db_input['hoarding_capex_cost']!=0):
        ui_inputs['hoarding cost']=db_input['hoarding_capex_cost']
    if(db_input['kiosk_capex_cost'] is not None and db_input['kiosk_capex_cost']!=0):
        ui_inputs['kiosk_cost']=db_input['kiosk_capex_cost']
    if(db_input['year_1_conversion'] is not None and db_input['year_1_conversion']!=0):
        ui_inputs['year1_conversion']=db_input['year_1_conversion']/100.0
    if(db_input['year_2_conversion'] is not None and db_input['year_2_conversion']!=0):
        ui_inputs['year2_conversion']=db_input['year_2_conversion']/100.0
    if(db_input['year_3_conversion'] is not None and db_input['year_3_conversion']!=0):
        ui_inputs['year3_conversion']=db_input['year_3_conversion']/100.0
    if(db_input['available_area'] is not None and db_input['available_area']!=0):
        ui_inputs['Ai']=db_input['available_area']
    if(db_input['annual_demand'] is not None and db_input['annual_demand']!=0):
        ui_inputs['Li']=db_input['annual_demand']
    if(db_input['margin_percentage'] is not None and db_input['margin_percentage']!=0):
        ui_inputs['Bipc']=db_input['margin_percentage']/100.0
    if(db_input['margin_rate_per_kwh'] is not None and db_input['margin_rate_per_kwh']!=0):
        ui_inputs['Birate']=db_input['margin_rate_per_kwh']
    if(db_input['energy_tariff_margin'] is not None and db_input['energy_tariff_margin']!=0):
        ui_inputs['Eg']=db_input['energy_tariff_margin']
    if(db_input['capex_bus_charger'] is not None and db_input['capex_bus_charger']!=0):
        ui_inputs['cabling_cost']=db_input['capex_bus_charger']

    
    updateParams = (
    ui_inputs["planning_scenario"],
    ui_inputs["backoff_factor"],
    yoe,
    ui_inputs["Ai"],
    ui_inputs["Li"],
    ui_inputs["Bipc"],
    ui_inputs["Birate"],
    ui_inputs["Eg"],
    ui_inputs["capex_2W"],
    ui_inputs["capex_3WS"],
    ui_inputs["capex_4WS"],
    ui_inputs["capex_4WF"],
    ui_inputs["cabling_cost"],
    ui_inputs["hoarding cost"],
    ui_inputs["kiosk_cost"],
    ui_inputs["year1_conversion"],
    ui_inputs["year2_conversion"],
    ui_inputs["year3_conversion"],
    ui_inputs["holiday_percentage"],
    ui_inputs["fast_charging"],
    ui_inputs["slow_charging"],
    int(ui_inputs["cluster"]),  # Convert to int (1 for True, 0 for False)
    ui_inputs["cluster_th"],
    int(ui_inputs["plot_dendrogram"]),
    idSelect  # This is the `id` of the record to update
)
    
    updateQuery = f"""
    UPDATE analysis_inputs
    SET
        planning_scenario = %s,
        backoff_factor = %s,
        years_of_analysis = %s,
        available_area = %s,
        annual_demand = %s,
        margin_percentage = %s,
        margin_rate_per_kwh = %s,
        energy_tariff_margin = %s,
        capex_2w_charger = %s,
        capex_3w_charger = %s,
        capex_4w_charger = %s,
        capex_4wf_charger = %s,
        capex_bus_charger = %s,
        hoarding_capex_cost = %s,
        kiosk_capex_cost = %s,
        year_1_conversion = %s,
        year_2_conversion = %s,
        year_3_conversion = %s,
        holiday_percentage = %s,
        fast_charging = %s,
        slow_charging = %s,
        cluster = %s,
        cluster_th = %s,
        plot_dendrogram = %s
    WHERE id = %s;
"""
    mycursor.execute(updateQuery, updateParams)
    mydb.commit()


    
    filename = str(filename)

    idSelect=str(idSelect)
    
    # Run analysis
    
    # Run analysis
    analysis,inputFile,u_df = analyze_sites(f'output/{idSelect}',filename, ui_inputs,idSelect,db_input)


    df = pd.read_excel(f'{inputFile}/Sites.xlsx')

# Count occurrences of "PP", "FB", and "BD" in the "Site category" column
    category_counts = df['Site category'].value_counts()

# Filter for "PP", "FB", and "BD" specifically
    pp_count = category_counts.get('PP', 0)
    fb_count = category_counts.get('FH', 0)
    bd_count = category_counts.get('BD', 0)

    update_query = f"""
UPDATE analysis_inputs
SET publicPlaces = {pp_count}, busDepots = {bd_count}, fleetHubs = {fb_count}
WHERE id = {idSelect};
"""
    mycursor.execute(update_query)
    
  
    if ui_inputs["cluster"] and os.path.exists(f"{analysis}cluster_destination_charging_evci_analysis.json"):
        try:
            df1Cluster= pd.read_json(f'{analysis}cluster_destination_charging_evci_analysis.json')
        except FileNotFoundError:
            raise HTTPException(status_code=500, detail="File not found.")
        
         

        df1Cluster['analysis_id']=db_input['id']
        df1Cluster['outputFile']="cluster_destination_charging_evci_analysis"
        df1Cluster['createdby']=db_input['createdBy']
        df1Cluster['utilization']=df1Cluster['utilization']*100
        df1Cluster['unserviced']=df1Cluster['unserviced']*100


        df1Cluster.insert(0, 'analysis_id', df1Cluster.pop('analysis_id'))  # Move 'analysis_id' to the first column
        df1Cluster.insert(1, 'outputFile', df1Cluster.pop('outputFile'))
   
   
    if ui_inputs["cluster"] and os.path.exists(f"{analysis}cluster_opportunity_charging_evci_analysis.json"):
        try:
            df4Cluster= pd.read_json(f'{analysis}cluster_opportunity_charging_evci_analysis.json')
        except FileNotFoundError:
            raise HTTPException(status_code=500, detail="File not found.")
        
         

        df4Cluster['analysis_id']=db_input['id']
        df4Cluster['outputFile']="cluster_opportunity_charging_evci_analysis"
        df4Cluster['createdby']=db_input['createdBy']
        df4Cluster['utilization']=df4Cluster['utilization']*100
        df4Cluster['unserviced']=df4Cluster['unserviced']*100


        df4Cluster.insert(0, 'analysis_id', df4Cluster.pop('analysis_id'))  # Move 'analysis_id' to the first column
        df4Cluster.insert(1, 'outputFile', df4Cluster.pop('outputFile'))


    df2Destination = pd.read_json(f'{analysis}initial_destination_charging_evci_analysis.json')
    df3Intial = pd.read_json(f'{analysis}initial_opportunity_charging_evci_analysis.json')


     
    df2Destination['createdby']=db_input['createdBy']
    df2Destination['unserviced']=df2Destination['unserviced']*100

    df2Destination['utilization']=df2Destination['utilization']*100
    df2Destination['analysis_id']=db_input['id']
    df2Destination['outputFile']="initial_destination_charging_evci_analysis"
    df2Destination['createdby']=db_input['createdBy']


    df2Destination.insert(0, 'analysis_id', df2Destination.pop('analysis_id'))  # Move 'analysis_id' to the first column
    df2Destination.insert(1, 'outputFile', df2Destination.pop('outputFile')) 

    df3Intial['analysis_id']=db_input['id']
    df3Intial['outputFile']="initial_opportunity_charging_evci_analysis"
    df3Intial['createdby']=db_input['createdBy']

    df3Intial['utilization']=df3Intial['utilization']*100
    df3Intial['unserviced']=df3Intial['unserviced']*100

    df3Intial.insert(0, 'analysis_id', df3Intial.pop('analysis_id'))  # Move 'analysis_id' to the first column
    df3Intial.insert(1, 'outputFile', df3Intial.pop('outputFile')) 




    insert_query = f"""
INSERT INTO analysis_responses (
    analysisInput_ID, output_for, location_name, latitude, longitude, 
    transformer_name, transformer_latitude, transformer_longitutde, transformer_distance, 
    number_of_vehicle, year_1, kiosk_hoarding, hoarding_margin, geometry, utiliztion, 
    unserviced, capex, opex, margin, max_vehicles, estimated_vehicles, createdBy
) VALUES ( %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 0, %s, %s, %s, %s, %s, %s, %s, %s)
"""


    if ui_inputs["cluster"] and os.path.exists(f"{analysis}cluster_destination_charging_evci_analysis.json"):
        df1Cluster.fillna(0, inplace=True)
        for _, row in df1Cluster.iterrows():
            mycursor.execute(insert_query, tuple(row))
   
    if ui_inputs["cluster"] and os.path.exists(f"{analysis}cluster_opportunity_charging_evci_analysis.json"):
        df4Cluster.fillna(0, inplace=True)
        for _, row in df4Cluster.iterrows():
            mycursor.execute(insert_query, tuple(row))
    
    df2Destination.fillna(0, inplace=True)
    for _, row in df2Destination.iterrows():
        mycursor.execute(insert_query, tuple(row))
    df3Intial.fillna(0, inplace=True)
    for _, row in df3Intial.iterrows():
        mycursor.execute(insert_query, tuple(row))


    insert_query = f"""
            INSERT INTO analysis_response_file_logs 
            (site_ID, analysisInput_ID, outputFor, excelFilePath, isActive, createdBy) 
            VALUES (%s, %s, %s, %s, %s,%s)
            """
    data = [
                
                (filename, idSelect, "initial_destination_charging_evci_analysis", analysis+"initial_destination_charging_evci_analysis.xlsx", "1", db_input['createdBy']),
                (filename, idSelect, "initial_opportunity_charging_evci_analysis", analysis+"initial_opportunity_charging_evci_analysis.xlsx", "1", db_input['createdBy'])
            ]
    
    if ui_inputs["cluster"] and os.path.exists(f"{analysis}cluster_destination_charging_evci_analysis.json"):
        data.append((filename, idSelect, "cluster_destination_charging_evci_analysis", analysis+"cluster_destination_charging_evci_analysis.xlsx", "1", db_input['createdBy']),)
    if ui_inputs["cluster"] and os.path.exists(f"{analysis}cluster_opportunity_charging_evci_analysis.json"):
        data.append((filename, idSelect, "cluster_opportunity_charging_evci_analysis", analysis+"cluster_opportunity_charging_evci_analysis.xlsx", "1", db_input['createdBy']),)
    for row in data:
        mycursor.execute(insert_query, row)

    mydb.commit()
    mycursor.close()
    mydb.close()


    import matplotlib.pyplot as plt

    fig, (ax1,ax2) = plt.subplots(1,2, figsize=(10,3))
    u_df['opportunity_charging']['initial'].hist(column='utilization',ax=ax1);
    u_df['destination_charging']['initial'].hist(column='utilization',ax=ax2);
    ax1.title.set_text('Opportunity charging')
    ax2.title.set_text('Destination charging')
    plt.tight_layout()

    fig.savefig(f'{analysis}Initial_charging_utilization_comparison.png', dpi=300, bbox_inches='tight')

    fig, (ax1,ax2) = plt.subplots(1,2, figsize=(10,3))
    u_df['opportunity_charging']['initial'].hist(column='unserviced',ax=ax1);
    u_df['destination_charging']['initial'].hist(column='unserviced',ax=ax2);
    ax1.title.set_text('Opportunity charging')
    ax2.title.set_text('Destination charging')
    plt.tight_layout()

    fig.savefig(f'{analysis}Unserviced_Initial_charging_utilization_comparison.png', dpi=300, bbox_inches='tight')



    if ui_inputs["cluster"] and os.path.exists(f"{analysis}cluster_destination_charging_evci_analysis.json") and os.path.exists(f"{analysis}cluster_opportunity_charging_evci_analysis.json"):
        fig, (ax1,ax2) = plt.subplots(1,2, figsize=(10,3))
        u_df['opportunity_charging']['cluster'].hist(column='utilization',ax=ax1);
        u_df['destination_charging']['cluster'].hist(column='utilization',ax=ax2);
        ax1.title.set_text('Opportunity charging')
        ax2.title.set_text('Destination charging')
        plt.tight_layout()

        fig.savefig(f'{analysis}Cluster_charging_utilization_comparison.png', dpi=300, bbox_inches='tight')

        fig, (ax1,ax2) = plt.subplots(1,2, figsize=(10,3))
        u_df['opportunity_charging']['cluster'].hist(column='unserviced',ax=ax1);
        u_df['destination_charging']['cluster'].hist(column='unserviced',ax=ax2);
        ax1.title.set_text('Opportunity charging')
        ax2.title.set_text('Destination charging')
        plt.tight_layout()

        fig.savefig(f'{analysis}unservicedCluster_charging_utilization_comparison.png', dpi=300, bbox_inches='tight')





    return {"status":"success","message":"generated"}


    
    
