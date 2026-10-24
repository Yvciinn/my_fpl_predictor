import pandas as pd
live = pd.read_csv(r'C:\Users\yacin\Documents\myfpl_predictor\python\fpl_live_dataset.csv')
print(live[['web_name', 'team']].head(10))