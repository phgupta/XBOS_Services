import pickle

import os
curr_path = os.path.abspath(os.path.dirname(__file__))

best_model_path = os.path.join(curr_path + '/models/{}/{}'.format('local-butcher-shop', 'best'))
model_file = open(best_model_path, 'rb')

best_model = pickle.load(model_file)

print(best_model)