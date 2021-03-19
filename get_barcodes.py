import pandas as pd
import json

def get_barcodes_for_child(child):
    """
    Get info for individual child in the taxonomy
    """
    return child['barcodes']
    

def get_barcodes(root_dictionary, rbr_df, level, root_name):
    """
    Returns list of lists
    Each row is a company mapped to the lowest level in the rbr
    """
    parent = root_dictionary['name']
    for child in root_dictionary['children']:
        info = get_barcodes_for_child(child)
        child_name = child['name']
        rbr_name = root_name + " Level " + str(level) + ": " + child_name
    
        for x in info:
            x = list(x.values())
            x.append(rbr_name)
            x.append(level)
            x.append(child['id'])
            found = False
            # remove duplicates
            for y in rbr_df:
                if y[:-2] == x[:-2]:
                    rbr_df.remove(y)
                    rbr_df.append(x)
                    found = True
            if found == False:
                rbr_df.append(x)
        level += 1
        rbr_df =  get_barcodes(child, rbr_df, level, root_name)
        level -= 1
    return rbr_df

def get_rbr_barcode_df(taxonomy_filepath):
    """
    Converts rbr list of lists to a dataframe
    """
    with open(taxonomy_filepath, 'r') as f: # open in readonly mode
        taxonomy = json.load(f)
    file_name = taxonomy_filepath.split("/")[-1]
    root_name = file_name.split(".")[0]
    rbr_df = get_barcodes(taxonomy['root'], rbr_df=[], level=1, root_name=root_name)
    rbr_df = pd.DataFrame(rbr_df)
    rbr_df.columns = ['barcode_id', 'analyst_id', 'rbr_level', 'level_number', 'rbr_id']
    return rbr_df
# Example:
# df = get_rbr_barcode_df("/Users/kalyanisubbiah/Syntax/taxonomy_pull/New_Real_asset.json")


