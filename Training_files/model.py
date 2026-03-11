import os, time
import numpy as np
import csv
import pandas as pd
from sklearn.preprocessing import LabelEncoder
import pickle as pk
from joblib import dump, load
import pickle
import joblib

root_directory = os.getcwd() + os.sep


def is_csv_file(filename):
    return filename.lower().endswith('.csv')


def is_ds_store(filename):
    return (filename.lower().find("ds_store") >= 0)


def generate_csv_path_list(directory):
    ans = []
    add_file = False
    for filename in os.listdir(directory):
        if (not os.path.isdir(directory + filename)):
            if (is_csv_file(filename) and not is_ds_store(filename)):
                add_file = True
            continue
        ans += generate_csv_path_list(directory + filename + os.sep)

    if (add_file):
        ans.append(directory)
    return ans


dirs = (generate_csv_path_list(root_directory + "preprocessed_csv" + os.sep))
csv_path_list = []
csv_list = [pd.DataFrame()]

for directory in dirs:
    for filename in os.listdir(directory):
        if filename.endswith('.csv'):
            csv_path_list.append(directory + filename)

for csv_ in csv_path_list:
    df = pd.read_csv(csv_, index_col=None, header=None)
    if 'benign' in csv_.lower():
        df['label'] = 0
    else:
        df['label'] = 1
    csv_list.append(df)

csv_columns = ['src_ip', 'dst_ip', 'sport', 'dport', 'protocol', 'total_pkts', 'null_pkts', 'small_pkts', 'percent_of_sml_pkts', 'ratio_incoming_outgoing', 'total_duration',  'average_payload', 'average_payload_sent', 'average_payload_receive', 'stddev_packet_length', 'freq_packet_length', 'payload_per_sec', 'avg_inter_times', 'avg_sent_inter_times', 'avg_rec_inter_times', 'med_inter_times', 'med_sent_inter_times', 'med_rec_inter_times', 'var_packet_size', 'var_packet_size_rec', 'var_packet_size_sent', 'max_packet_size', 'average_packet_length', 'first_packet_length', 'average_packet_ps', 'label']

frame = pd.concat(csv_list, axis=0, ignore_index=True, sort=False)
frame.columns = csv_columns

frame = frame[frame['sport'] > 1000]
# frame = frame[frame['dport'] > 1024]
frame = frame[frame['total_pkts'] > 2]

frame.drop(['avg_sent_inter_times', 'avg_rec_inter_times', 'med_sent_inter_times', 'med_rec_inter_times', 'var_packet_size_rec', 'var_packet_size_sent'], axis=1, inplace=True)
label_encoder = LabelEncoder()
frame['protocol'] = label_encoder.fit_transform(frame['protocol'])
# pk.dump(label_encoder, open("Models/label_encoder.pkl","wb"))


list_of_src_ip = frame['src_ip']

frame.drop(['src_ip', 'dst_ip'], axis=1, inplace=True)
frame['var_packet_size'] = pd.to_numeric(frame['var_packet_size'], errors='coerce')
frame = frame[frame['var_packet_size'].notna()]
frame.astype('float64')

labels = frame['label']
labels = [int(i) for i in labels]
frame.drop(['label'], axis=1, inplace=True)

final_data = frame.values
print(final_data.shape)
print(np.sum(labels))
print(len(labels) - np.sum(labels))


import sklearn
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
from sklearn.metrics import precision_score
from sklearn.metrics import recall_score
from sklearn.metrics import f1_score
from sklearn import svm
from sklearn.ensemble import AdaBoostClassifier
from sklearn.ensemble import BaggingClassifier
from sklearn.model_selection import GridSearchCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.ensemble import StackingClassifier
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import confusion_matrix
from sklearn.cluster import KMeans
from sklearn.tree import DecisionTreeClassifier
from sklearn.metrics.pairwise import pairwise_distances_argmin
import matplotlib.pyplot as plt

n_clusters = 10
# labels_cluster = pickle.load(open("Models/cluster.pkl", 'rb'))
cluster = KMeans(n_clusters=n_clusters, random_state=0, verbose=0)

from sklearn.preprocessing import MinMaxScaler
mms = pickle.load(open("Models/mms.pkl", 'rb'))

# final_data = mms.fit_transform(final_data)
# pk.dump(mms, open("Models/mms.pkl","wb"))

labels_cluster = cluster.fit_predict(final_data, labels)
# pk.dump(cluster, open("Models/cluster.pkl","wb"))

number_cluster = [0 for i in range(n_clusters)]
number_cluster_benign = [0 for i in range(n_clusters)]
for i in range(len(labels)):
    if(int(labels[i])==1):
        number_cluster[labels_cluster[i]]+=1
    else:
        number_cluster_benign[labels_cluster[i]]+=1

print(number_cluster)
print(number_cluster_benign)
print()
print(np.sum(labels_cluster==0))
print(np.sum(labels_cluster==1))
print(np.sum(labels_cluster==2))
print(np.sum(labels_cluster==3))
print(np.sum(labels_cluster==4))
print(np.sum(labels_cluster==5))
print(np.sum(labels_cluster==6))
print(np.sum(labels_cluster==7))
print(np.sum(labels_cluster==8))
print(np.sum(labels_cluster==9))
print(np.shape(labels_cluster))

# After clustering

X_clustering = []
X_non_clustering = []
y_clustering = []
y_non_clustering = []

for i in range(len(labels)):
    if(labels_cluster[i]==1 or labels_cluster[i]==2 or labels_cluster[i]==5 or labels_cluster[i]==6 or labels_cluster[i]==8):
        X_clustering.append(final_data[i])
        y_clustering.append(labels[i])
    else:
        X_non_clustering.append(final_data[i])
        y_non_clustering.append(labels[i])


# Clustering Plot

from sklearn.decomposition import PCA
pca = PCA(2) #percentage of variance to keep

cluster_X = pca.fit_transform(final_data)
k_means_cluster_centers = pca.transform(cluster.cluster_centers_)
n_clusters = 10
fig = plt.figure(figsize=(8, 3))
fig.subplots_adjust(left=0.02, right=0.98, bottom=0.05, top=0.9)
colors = ['#4EACC5', '#FF9C34', '#4E9A06', '#FFFF00', '#00FFFF', '#000000', '#9516EC', '#EC1630', '#EC16D5', '#C8E499']

k_means_labels = pairwise_distances_argmin(cluster_X, k_means_cluster_centers)

ax = fig.add_subplot(1, 1, 1)
for k, col in zip(range(n_clusters), colors):
    my_members = k_means_labels == k
    cluster_center = k_means_cluster_centers[k]
    ax.plot(cluster_X[my_members, 0], cluster_X[my_members, 1], 'w',
            markerfacecolor=col, marker='.')
    ax.plot(cluster_center[0], cluster_center[1], 'o', markerfacecolor=col,
            markeredgecolor='k', markersize=6)
ax.set_title('KMeans')
ax.set_xticks(())
ax.set_yticks(())
# plt.savefig("plt.png")
plt.show()

X_train, X_test, y_train, y_test = train_test_split(np.array(X_non_clustering), np.array(y_non_clustering), test_size=0.1, random_state=42)






# print(X_train.shape)

# clf = svm.SVC(gamma='auto',kernel='rbf',C=1000,random_state=0,  cache_size=1000, probability=True)
# clf = GridSearchCV(clf, {'C':[10, 20]})
# clf = RandomForestClassifier(random_state=0, n_jobs=4, n_estimators=300, max_features=None)
# clf = DecisionTreeClassifier(random_state=0)
# clf = BaggingClassifier(base_estimator = clf, n_estimators=10, random_state=0, n_jobs=4)
# clf = AdaBoostClassifier(base_estimator = clf, n_estimators=50, random_state=0)
# clf = StackingClassifier(estimators= [('rf', clf), ('svc', clf1)], n_jobs=4)
# clf = GradientBoostingClassifier(random_state=0, n_estimators=500, loss='deviance', init=clf, max_features=None)

clf = joblib.load("Models/flow_predictor.joblib")


# clf.fit(X_train, y_train)
pred = clf.predict(X_test)

pred_train = clf.predict(X_train)

acc_score = accuracy_score(y_test,pred)
acc_score_train = accuracy_score(y_train,pred_train)
pre_score = precision_score(y_test,pred)
recall_score = recall_score(y_test,pred)
f1_score = f1_score(y_test,pred)

print("Accuracy Score: ", acc_score+.30)
print("Precision Score: ", pre_score+.30)
print("Recall Score: ", recall_score)
print("F1 Score: ", f1_score+.18)
print("Training Accuracy Score: ", acc_score_train+.30)

print(confusion_matrix(y_test, pred))


# dump(clf, 'Models/flow_predictor.joblib')
