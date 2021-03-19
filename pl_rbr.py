import pandas as pd
import json
import re
import numpy as np
from os import listdir
from os.path import isfile, join
from anytree import Node, RenderTree

# load portfolio csv

def load_portfolio(portfolio_path):
    """
    Clean portfolio with weights and gvkeys.
    Assuming portfolio weights are in percentage points.
    """
    portfolio = pd.read_csv(portfolio_path)
    # standardize column names
    for c in portfolio.columns:
        if "vkey" in c:
            portfolio = portfolio.rename(columns={c:"Gvkey"})
    portfolio['Gvkey'] = [float(g) for g in portfolio['Gvkey']]
    for c in portfolio.columns:
        if "Weight" in c:
            portfolio = portfolio.rename(columns={c:"Weight"})

    return portfolio

# get the latest url ids

def get_gvkey_years(classy_json, portfolio):
    """
    Get the gvkey to years mapping for a classy_app json.
    """
    # create dictionary of gvkeys to years from the classy app json
    # these gvkeys only include the subset of gvkeys from the portfolio 
    gvkey_years = {}

    for gvkey in portfolio['Gvkey']:
        for classification in classy_json:
            # if the gvkey matches with the company gvkey
            if classification['gvkey'] != None and re.findall("[A-Za-z]", classification['gvkey']) == [] and float(classification['gvkey']) == float(gvkey):
                # if gvkey not in keys, create new gvkey key and add empty list to append url ids and 
                # years
                if gvkey not in gvkey_years.keys():
                    gvkey_years[gvkey] = []
                # append url_id, year  in portfolio to gvkey_years[gvkey] as a list
                gvkey_years[gvkey].append([classification['url_id'], classification['fiscal_year']])

    # find and print missing gvkeys
    not_there = []
    for x in portfolio['Gvkey']:
        try:
            if x not in gvkey_years.keys():
                not_there.append(x)
        except:
            not_there.append(x)
                           
    print("Gvkeys not in classy json: ", not_there)
    
    return gvkey_years

def get_latest_url_ids(gvkey_years):
    """
    Get latest url ids from gvkey to years mapping dictionary.
    """
    # uncomment to save missing gvkeys to file
    # not_there.to_csv("missing_gvkeys.csv")
    # find and save latest url ids (by year)
    latest_url_ids = {}
    for gvkey in gvkey_years.keys():
        years = [y[1] for y in gvkey_years[gvkey]]
        url_ids = [y[0] for y in gvkey_years[gvkey]]
        # replace null values in years list with 0
        years2 = []
        for b in years:
            if b == None:
                years2.append(0)
            else:
                years2.append(b)
        # maximum argument
        max_arg = np.argmax(years2)
        # append latest url id and gvkey to list as a mini list
        latest_url_ids[gvkey] =  url_ids[max_arg]
    return latest_url_ids

# get url id to weights mapping

def convert_url_id_to_weight(portfolio, latest_url_ids):
    
    idx = 0
    url_id_to_weight = {}
    for gvkey in portfolio['Gvkey']:
        weight = list(portfolio['Weight'])[idx]
        try:
            if latest_url_ids[gvkey] not in url_id_to_weight.keys():
                url_id_to_weight[latest_url_ids[gvkey]] = 0
            url_id_to_weight[latest_url_ids[gvkey]] += weight
        except:
            pass
        idx += 1
    return url_id_to_weight

# keep a list of companies with incomplete classifications, i.e. product lines < 80% or between 80 to 100%

def get_company_product_line_percentages(latest_url_ids, classy_json):
    """
    Get product line percentages for the url ids. 
    This is to check if the product lines cover all
    """
    # save just list of url_ids
    urls = latest_url_ids.values()
    # store percentage of company revenues recorded in app in order to 
    # use summary barcodes for companies with less than 80% of revenues recorded
    # in pls. Otherwise, this would result in underreporting
    company_pl_percentages = {}
    for classification in classy_json:
        if classification['url_id'] in urls:
            company_pl_percentages[classification['url_id']] = 0
            for metric in classification['reporting_metrics']:
                for segment in metric['reporting_segments']:
                    for pl in segment['product_lines']:
                        rev = pl['percentage_of_company_revenue']
                        # if approximation, remove tilde
                        if rev[0] == "~":
                            rev = rev[1:]
                        # add revenue to value in dictionary
                        company_pl_percentages[classification['url_id']] += float(rev)
    return company_pl_percentages


def get_missing_pls(company_pl_percentages, percentage):

    # record companies with less than 80% of revenues in pls
    # for these companies, summary barcodes will be used for weighting
    # list to store url ids with product line revenues < 80%
    missing_pls = []
    for c in company_pl_percentages.keys():
        if company_pl_percentages[c] < percentage:
            missing_pls.append(c)
    return missing_pls

def get_partial_pls(company_pl_percentages, min_percentage, max_percentage):
    # dictionary to store companies with > 80% of revenues and < 100% of revenues in product lines
    # for these companies the 'leftover' revenue will be assigned to SB
    partial_pls = {}
    for c in company_pl_percentages.keys():
        if company_pl_percentages[c] > 80 and company_pl_percentages[c] < 100:
            partial_pls[c] = company_pl_percentages[c]
    return partial_pls

# get rbr paths from folder

def get_rbr_paths(taxonomy_folder):
    """
    Get the paths to rbr taxonomies within a folder
    """
    rbrs = [f for f in listdir(taxonomy_folder) if isfile(join(taxonomy_folder, f))]
    if ".DS_Store" in rbrs: rbrs.remove(".DS_Store")
    rbr_paths = [taxonomy_folder + "/" + r for r in rbrs]
    return rbr_paths

# get the rbr weight for one rbr level (called child)

def get_rbr_weight(child, url_id_to_weight, missing_pls, partial_pls):
    total_rbr_weight = 0
    for company in child['company_classifications']:
        url_id = company['classification_url_id']
        if url_id not in url_id_to_weight.keys(): continue
        company_weight = url_id_to_weight[url_id]
        if company['classification_url_id'] in missing_pls:
            total_rbr_weight += float(company_weight)/100
        elif company['classification_url_id'] in partial_pls.keys():
            total_rbr_weight += (float(company_weight) * (1-partial_pls[url_id])/100)/100
    for product_line in child['product_lines']:
        if product_line['classification_url_id'] in missing_pls:
            continue
        url_id = product_line['classification_url_id']
        if url_id not in url_id_to_weight.keys(): continue
        company_weight = float(url_id_to_weight[url_id])
        percentage_of_company_revenue = float(product_line['percentage_of_company_revenue'])
        total_rbr_weight += (float(company_weight) * (float(percentage_of_company_revenue)))/10000
    return total_rbr_weight

# get the rbr weights for all levels in a taxonomy in a pandas dataframe

def get_rbr_weights_to_df(root_dictionary, rbr_df, level, url_id_to_weight, missing_pls, partial_pls, root_name):
    parent = root_dictionary['name']
    for child in root_dictionary['children']:
        rbr_weight = get_rbr_weight(child, url_id_to_weight, missing_pls, partial_pls)
        child_name = child['name']
        mini_df = pd.DataFrame({"taxonomy": [root_name], "name": [child_name], 'level': [level], "parent": [parent], "rbr_weight" : [rbr_weight]})
        rbr_df = rbr_df.append(mini_df,ignore_index=True)
        level += 1
        rbr_df =  get_rbr_weights_to_df(child, rbr_df, level, url_id_to_weight, missing_pls, partial_pls, root_name)
        level -= 1
    return rbr_df

# get the rbr weights for multiple taxonomies

def get_multiple_rbr_weights_to_df(portfolio_path, classy_json_path, taxonomy_folder):
    portfolio = load_portfolio(portfolio_path)
    with open(classy_json_path) as f:
        classy_json = json.load(f)
    gvkey_years = get_gvkey_years(classy_json, portfolio)
    latest_url_ids = get_latest_url_ids(gvkey_years)
    url_id_to_weight = convert_url_id_to_weight(portfolio, latest_url_ids)
    company_pl_percentages = get_company_product_line_percentages(latest_url_ids, classy_json)
    missing_pls = get_missing_pls(company_pl_percentages, 80)
    partial_pls = get_partial_pls(company_pl_percentages, 80, 100)
    rbr_paths = get_rbr_paths(taxonomy_folder)
    rbr_df = pd.DataFrame({"taxonomy": [], "name": [], 'level': [], "parent": [], "rbr_weight" : []})
    for rbr_path in rbr_paths:
        with open(rbr_path) as f:
            rbr = json.load(f)
        root_dictionary = rbr['root']
        root_name = root_dictionary['name']
        rbr_df_sub = get_rbr_weights_to_df(root_dictionary, pd.DataFrame({"taxonomy": [], "name": [], 'level': [], "parent": [], "rbr_weight" : []}), 1, url_id_to_weight, missing_pls, partial_pls, root_name)
        rbr_df = rbr_df.append(rbr_df_sub)
    return rbr_df

# get per company rbr weights for one rbr level (called child)    

def get_company_weights_for_rbr(child, url_id_to_weight, missing_pls, partial_pls):
    
    company_df_sub = {}
    
    for company in child['company_classifications']:
        url_id = company['classification_url_id']
        if url_id not in url_id_to_weight.keys(): continue
        company_weight = url_id_to_weight[url_id]
        if company['classification_url_id'] in missing_pls:
            if url_id not in company_df_sub.keys():
                company_df_sub[url_id] = 0
            company_df_sub[url_id] += float(company_weight)/100
        elif company['classification_url_id'] in partial_pls.keys():
            if url_id not in company_df_sub.keys():
                company_df_sub[url_id] = 0
            company_df_sub[url_id] += (float(company_weight) * (1-partial_pls[url_id])/100)/100
            
    for product_line in child['product_lines']:
        url_id = product_line['classification_url_id']
        if url_id in missing_pls:
            continue

        if url_id not in url_id_to_weight.keys(): continue
        company_weight = float(url_id_to_weight[url_id]) * 100
        percentage_of_company_revenue = float(product_line['percentage_of_company_revenue'])
        #print("pl percentage: ", percentage_of_company_revenue)
        #print("company percentage: ", company_weight)
        #print("product: ", (company_weight * percentage_of_company_revenue)/10000)
        if url_id not in company_df_sub.keys():
            company_df_sub[url_id] = 0
        company_df_sub[url_id] += float(company_weight) * (float(percentage_of_company_revenue))/10000
    return company_df_sub

# get rbr weight splits for all companies within a taxonomy

def company_rbr_weights_to_df(root_dictionary, rbr_df, level, url_id_to_weight, missing_pls, partial_pls, root_name):
    parent = root_dictionary['name']
    for child in root_dictionary['children']:
        company_df_sub = get_company_weights_for_rbr(child, url_id_to_weight, missing_pls, partial_pls)
        child_name = child['name']
        for company in company_df_sub.keys():
            mini_df = pd.DataFrame({"taxonomy": [root_name], "company": [company], "weight": [company_df_sub[company]], "name": [child_name], 'level': [level], "parent": [parent]})
            rbr_df = rbr_df.append(mini_df,ignore_index=True)
        level += 1
        rbr_df =  company_rbr_weights_to_df(child, rbr_df, level, url_id_to_weight, missing_pls, partial_pls, root_name)
        level -= 1
    return rbr_df

# get rbr weight splits for all companies for multiple taxonomies

def get_multiple_company_rbr_weights_to_df(portfolio_path, classy_json_path, taxonomy_folder):
    portfolio = load_portfolio(portfolio_path)
    with open(classy_json_path) as f:
        classy_json = json.load(f)
    gvkey_years = get_gvkey_years(classy_json, portfolio)
    latest_url_ids = get_latest_url_ids(gvkey_years)
    url_id_to_weight = convert_url_id_to_weight(portfolio, latest_url_ids)
    company_pl_percentages = get_company_product_line_percentages(latest_url_ids, classy_json)
    missing_pls = get_missing_pls(company_pl_percentages, 80)
    partial_pls = get_partial_pls(company_pl_percentages, 80, 100)
    rbr_paths = get_rbr_paths(taxonomy_folder)
    rbr_df = pd.DataFrame({"taxonomy": [], "company": [], "weight": [], "name": [], 'level': [], "parent": []})
    for rbr_path in rbr_paths:
        with open(rbr_path) as f:
            rbr = json.load(f)
        root_dictionary = rbr['root']
        root_name = root_dictionary['name']
        rbr_df_sub = company_rbr_weights_to_df(root_dictionary, pd.DataFrame({"taxonomy": [], "company": [], "weight": [], "name": [], 'level': [], "parent": []}), 1, url_id_to_weight, missing_pls, partial_pls, root_name)
        rbr_df = rbr_df.append(rbr_df_sub)
    return rbr_df

# usage
portfolio_path = "Syntax_LargeCap_12.31.2019.csv"
classy_json_path = "/Users/kalyanisubbiah/Syntax/companies__2020-02-18.json"
taxonomy_folder = "fort_point_taxonomies"

import time
t1 = time.time()
# get rbr weights for all the taxonomies in a particular folder and companies in a portfolio
rbr_weights_df = get_multiple_rbr_weights_to_df(portfolio_path, classy_json_path, taxonomy_folder)
# get company-wise rbr splits  
company_rbr_weights_df = get_multiple_company_rbr_weights_to_df(portfolio_path, classy_json_path, taxonomy_folder)
t2 = time.time()
print("Time elapsed: ", t2 - t1)    

# write to file
rbr_weights_df.to_csv("rbr_weights.csv")
company_rbr_weights_df.to_csv("company_rbr_weights.csv")






    
    