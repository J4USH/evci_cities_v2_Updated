from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import mysql.connector
from decimal import Decimal
from evci_tool.analysis import analyze_sites
import json
import pandas as pd

app = FastAPI()

# Pydantic model to define input structure
class AnalyzeRequest(BaseModel):
    analysisInput_ID: int
    site_id:int
    

# Default UI inputs
ui_inputs = { 
    "planning_scenario": "Public Places",
    "years_of_analysis": [1, 2, 3],
    "Ai": 50,
    "Li": 1500,
    "Bipc": .25,
    "Birate": 3.5,
    "Eg": 5.5,
    "backoff_factor": 1,
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
    "cluster_th": 0.02,
    "plot_dendrogram": True
}

@app.post("/analyze")
async def analyze(request: AnalyzeRequest):
    idSelect = request.analysisInput_ID
    filename = request.site_id
    


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
        return {"status": "failure","message":"analysis not generated successfully"}

    db_input = results[0]

    # Close database connection
    

    # Format db_input for compatibility
    for key, value in db_input.items():
        if isinstance(value, Decimal):
            db_input[key] = float(value)
        elif key == "years_of_analysis":  
            db_input[key] = list(range(1, db_input[key]+1))
        

    # Override defaults with database values if present
    for key in ui_inputs:
        if key in db_input:
            if db_input[key] is not None:
                ui_inputs[key] = db_input[key]

    
    if(db_input['capex_2w_charger'] is not None):
        ui_inputs['capex_2W']=db_input['capex_2w_charger']
    if(db_input['capex_3w_charger'] is not None):
        ui_inputs['capex_3WS']=db_input['capex_3w_charger']
    if(db_input['capex_4w_charger'] is not None):
        ui_inputs['capex_4WS']=db_input['capex_4w_charger']
    if(db_input['capex_4wf_charger'] is not None):
        ui_inputs['capex_4WF']=db_input['capex_4wf_charger']
    if(db_input['hoarding_capex_cost'] is not None):
        ui_inputs['hoarding cost']=db_input['hoarding_capex_cost']
    if(db_input['kiosk_capex_cost'] is not None):
        ui_inputs['kiosk_cost']=db_input['kiosk_capex_cost']
    if(db_input['year_1_conversion'] is not None):
        ui_inputs['year1_conversion']=db_input['year_1_conversion']
    if(db_input['year_2_conversion'] is not None):
        ui_inputs['year2_conversion']=db_input['year_2_conversion']
    if(db_input['year_3_conversion'] is not None):
        ui_inputs['year3_conversion']=db_input['year_3_conversion']
    


    if ui_inputs["cluster"] == 1:
        ui_inputs["cluster"]=True
        print(ui_inputs["cluster"])
    else:
        ui_inputs["cluster"]=False

    if ui_inputs["plot_dendrogram"] == 1:
        ui_inputs["plot_dendrogram"]=True
    else:
        ui_inputs["plot_dendrogram"]=False
    filename = str(filename)

    idSelect=str(idSelect)
    
    # Run analysis
    
        # Run analysis
    analysis,inputFile = analyze_sites(f'output/{idSelect}',filename, ui_inputs)


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

    if ui_inputs["cluster"]:
        df1Cluster= pd.read_json(f'{analysis}cluster_destination_charging_evci_analysis.json')
        df1Cluster['analysis_id']=db_input['id']
        df1Cluster['outputFile']="cluster_destination_charging_evci_analysis"
        df1Cluster['createdby']=db_input['createdBy']


        df1Cluster.insert(0, 'analysis_id', df1Cluster.pop('analysis_id'))  # Move 'analysis_id' to the first column
        df1Cluster.insert(1, 'outputFile', df1Cluster.pop('outputFile'))




    df2Destination = pd.read_json(f'{analysis}initial_destination_charging_evci_analysis.json')
    df3Intial = pd.read_json(f'{analysis}initial_opportunity_charging_evci_analysis.json')


     
    df2Destination['createdby']=db_input['createdBy']



    df2Destination['analysis_id']=db_input['id']
    df2Destination['outputFile']="initial_destination_charging_evci_analysis"
    df2Destination['createdby']=db_input['createdBy']


    df2Destination.insert(0, 'analysis_id', df2Destination.pop('analysis_id'))  # Move 'analysis_id' to the first column
    df2Destination.insert(1, 'outputFile', df2Destination.pop('outputFile')) 

    df3Intial['analysis_id']=db_input['id']
    df3Intial['outputFile']="initial_opportunity_charging_evci_analysis"
    df3Intial['createdby']=db_input['createdBy']

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


    if ui_inputs["cluster"]:
        df1Cluster.fillna(0, inplace=True)
        for _, row in df1Cluster.iterrows():
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
                (filename, idSelect, "cluster_destination_charging_evci_analysis", analysis+"cluster_destination_charging_evci_analysis.xlsx", "1", db_input['createdBy']),
                (filename, idSelect, "initial_destination_charging_evci_analysis", analysis+"initial_destination_charging_evci_analysis.xlsx", "1", db_input['createdBy']),
                (filename, idSelect, "initial_opportunity_charging_evci_analysis", analysis+"initial_opportunity_charging_evci_analysis.xlsx", "1", db_input['createdBy'])
            ]
    for row in data:
        mycursor.execute(insert_query, row)

    mydb.commit()
    mycursor.close()
    mydb.close()

    return {"status":"success","message":"generated"}


    
    
