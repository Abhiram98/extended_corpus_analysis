import pickle
from scipy import stats

with open('evaluator/hitmis_it10.pickle', 'rb') as f:
    hm10 = pickle.load(f)
with open('evaluator/hitmis_it_3.pickle', 'rb') as f:
    hm3 = pickle.load(f)

print("hi")

hm10_agg = {}
for docid in hm10:
    hm10_agg[docid] = sum(hm10[docid])

hm3_agg = {}
for docid in hm3:
    hm3_agg[docid] = sum(hm3[docid])

x = []
y = []
for docid in hm10_agg:
    x.append(hm10_agg[docid])
    y.append(hm3_agg[docid])

print(stats.wilcoxon(x,y))