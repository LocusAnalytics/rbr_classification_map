# rbr-weight-by-product-line
Taking a portfolio (mapping of company gvkeys to weights in a portfolio), the classy_app json and rbr taxonomy as inputs, output the weights of the rbrs calculated by product line in the rbr taxonomy (with a few exceptions for incomplete classifications). A second dataframe for each company's share in the rbrs is also produced. 

# Run program
portfolio_path = "Syntax_LargeCap_12.31.2019.csv"
classy_json_path = "/Users/kalyanisubbiah/Syntax/companies__2020-02-18.json"
taxonomy_folder = "fort_point_taxonomies"

import time
t1 = time.time()
#### get rbr weights for all the taxonomies in a particular folder and companies in a portfolio
rbr_weights_df = get_multiple_rbr_weights_to_df(portfolio_path, classy_json_path, taxonomy_folder)
#### get company-wise rbr splits  
company_rbr_weights_df = get_multiple_company_rbr_weights_to_df(portfolio_path, classy_json_path, taxonomy_folder)
t2 = time.time()
print("Time elapsed: ", t2 - t1)    

#### write to file
rbr_weights_df.to_csv("rbr_weights.csv")
company_rbr_weights_df.to_csv("company_rbr_weights.csv")

