import os, time
import sys
import numpy
from collections import Counter
from scapy.utils import RawPcapReader
from scapy.layers.l2 import Ether, CookedLinux
from scapy.layers.inet import IP, TCP, UDP
from scapy.packet import NoPayload
import numpy as np
import csv
import pandas as pd
import sklearn
import pickle as pk
from joblib import dump, load
from os import path as osp

file_path = sys.argv[1]

CSV_FILENAME = "flows_preprocessed_with_prediction" + ".csv"

TXT_FILENAME = "result.txt"

Benign_class_name = "Benign"
Botnet_class_name = "Botnet"

class Flow:

	def __init__(self):

		self.count = 0

		self.MICROSECOND = 10**6

		self.src_ip = None 
		self.dst_ip = None
		self.sport = None
		self.dport = None
		self.protocol = None

		self.total_duration = 0
		self.first_packet_timestamp = 0
		self.last_packet_timestamp = 0
		self.total_num_packets = 0

		self.packet_length = []

		self.null_packets = 0

		self.tcp_payload = 0
		self.udp_payload = 0
		self.received_payload = 0
		self.sent_payload = 0

		self.other_protocol = 0

		self.total_size_taken = 0

		self.SMALL_PACKET_THRESHOLD = 5 * 1024 * 1024 # in bytes - 5 MB
		self.small_packets = 0

		self.inter_arrival_times = []
		self.inter_arrival_times_send = []
		self.inter_arrival_times_receive = []

		self.count_sent = 0
		self.count_receive = 0
		self.last_sent_time = 0
		self.last_receive_time = 0

		self.packet_size = []
		self.packet_size_sent = []
		self.packet_size_receive = []

	def get_features(self):

		self.total_duration = self.last_packet_timestamp - self.first_packet_timestamp

		count_non_ip_packets = self.total_num_packets - self.count

		total_payload = self.udp_payload + self.tcp_payload
		
		ratio_of_incoming_to_outgoing = 0

		if (self.count > 0):
			average_payload = float(total_payload) / float(self.count)
		else:
			average_payload = 0

		if (self.count_sent > 0):
			average_payload_sent = float(self.sent_payload) / float(self.count_sent)
		else:
			average_payload_sent = 0

		if (self.count_receive > 0):
			average_payload_receive = float(self.received_payload) / float(self.count_receive)
			ratio_of_incoming_to_outgoing = float(self.count_sent) / float(self.count_receive)
		else:
			average_payload_receive = 0
		percent_of_small_packets = 0
		if (self.total_num_packets > 0):
			percent_of_small_packets = float(self.small_packets * 100) / float(self.total_num_packets)


		stddev_packet_length = np.std(self.packet_length) if len(self.packet_length) > 0 else 0

		if len(self.packet_length) > 0:
			counter = Counter(self.packet_length)
			mode_packet_length, freq_packet_length = counter.most_common(1)[0]
		else:
			mode_packet_length, freq_packet_length = 0, 0

		avg_inter_times = np.mean(self.inter_arrival_times) if len(self.inter_arrival_times) > 0 else 0
		avg_sent_inter_times = np.mean(self.inter_arrival_times_send) if len(self.inter_arrival_times_send) > 0 else 0
		avg_rec_inter_times = np.mean(self.inter_arrival_times_receive) if len(self.inter_arrival_times_receive) > 0 else 0

		med_inter_times = np.median(self.inter_arrival_times) if len(self.inter_arrival_times) > 0 else 0
		med_sent_inter_times = np.median(self.inter_arrival_times_send) if len(self.inter_arrival_times_send) > 0 else 0
		med_rec_inter_times = np.median(self.inter_arrival_times_receive) if len(self.inter_arrival_times_receive) > 0 else 0

		var_packet_size = np.var(self.packet_size) if len(self.packet_size) > 0 else 0
		var_packet_size_sent = np.var(self.packet_size_sent) if len(self.packet_size_sent) > 0 else 0
		var_packet_size_rec = np.var(self.packet_size_receive) if len(self.packet_size_receive) > 0 else 0

		max_packet_size = max(self.packet_size) if len(self.packet_size) > 0 else 0
		# Reconnection , total number of bytes --  is this file size?, 
		# average bits/s =  total payload / total duration ?

		if (self.count > 0):
			freq_packet_length = float(freq_packet_length) / float(self.count)

		if (self.total_duration > 0):
			total_payload = float(total_payload) / float(self.total_duration)
		else:
			total_payload = 0.0
		file_feature_list_1 = [self.total_num_packets, self.null_packets, self.small_packets, percent_of_small_packets, ratio_of_incoming_to_outgoing, self.total_duration,  average_payload, average_payload_sent, average_payload_receive]
		file_feature_list_2 = [stddev_packet_length, float(freq_packet_length), total_payload, avg_inter_times, avg_sent_inter_times, avg_rec_inter_times]
		file_feature_list_3 = [med_inter_times, med_sent_inter_times, med_rec_inter_times, var_packet_size, var_packet_size_rec,var_packet_size_sent, max_packet_size]

		# this was in first paper

		average_packet_length = np.mean(self.packet_length) if len(self.packet_length) > 0 else 0
		first_packet_length = self.packet_length[0] if len(self.packet_length) > 0 else 0
		if (self.total_duration > 0):
			average_packet_ps = float(self.count * self.MICROSECOND) / float(self.total_duration)
		else:
			average_packet_ps = 0
		file_feature_list_4 = [average_packet_length, first_packet_length, average_packet_ps]

		file_features = [self.src_ip, self.dst_ip, self.sport, self.dport, self.protocol]

		file_features += file_feature_list_1 + file_feature_list_2 + file_feature_list_3 + file_feature_list_4
		file_features = [0 if (isinstance(x, float) and np.isnan(x)) else x for x in file_features]

		return file_features

def generate_connections(file_path, flows_dict):

	start = time.process_time()

	print ("generating features for:", file_path)

	other_protocol = 0


	MICROSECOND = 10**6


	for (pkt_data, pkt_metadata) in RawPcapReader(file_path):

		# if 'usec' not in pkt_metadata:
		# 	continue


		ether_pkt = Ether(pkt_data)
		if ('type' not in ether_pkt.fields):
			ether_pkt = CookedLinux(pkt_data)
   
		if not hasattr(ether_pkt,"type") or ether_pkt.type != 0x0800:
			continue

		current_time_stamp = ether_pkt.time * MICROSECOND

		ip_pkt = ether_pkt[IP]
		src_ip = ip_pkt.src 
		dst_ip = ip_pkt.dst 

		is_sender = False
		is_receiver = False
		is_null_packet = False




		# if (src_ip in ip_addr):
		# 	is_sender = True

		# 	packet_size_sent.append(len(pkt_data))
		# 	if (count_sent != 0):
		# 		inter_arrival_times_send.append(current_time_stamp - last_sent_time)

		# 	last_sent_time = current_time_stamp
		# 	count_sent += 1

		# if (dst_ip in ip_addr):
		# 	is_receiver = True
		# 	packet_size_receive.append(len(pkt_data))

		# 	if (count_receive != 0):
		# 		inter_arrival_times_receive.append(current_time_stamp - last_receive_time)
		# 	count_receive += 1
		# 	last_receive_time = current_time_stamp



		current_payload = 0
		protocol = ""
		
		if (TCP in ether_pkt):
			tcp_pkt = ether_pkt[TCP]
			sport = tcp_pkt.sport
			dport = tcp_pkt.dport
			protocol = "TCP"
			
				
		elif (UDP in ether_pkt):
			udp_pkt = ether_pkt[UDP]
			sport = udp_pkt.sport
			dport = udp_pkt.dport
			protocol = "UDP"

		else:
			other_protocol += 1
			continue

		key_ = str(src_ip) + "_" + str(dst_ip) + "_" + str(sport) + "_" + str(dport) + "_" + str(protocol)

		if(key_ not in flows_dict):
			flows_dict[key_] = Flow()
			flows_dict[key_].src_ip = src_ip 
			flows_dict[key_].dst_ip = dst_ip
			flows_dict[key_].sport = sport
			flows_dict[key_].dport = dport
			flows_dict[key_].protocol = protocol


		flow_ = flows_dict[key_]

		flow_.total_num_packets += 1

		if (flow_.total_num_packets == 1):
			flow_.first_packet_timestamp = current_time_stamp
		else:
			flow_.inter_arrival_times.append(current_time_stamp - flow_.last_packet_timestamp)
			assert(current_time_stamp >= flow_.last_packet_timestamp)
		
		flow_.last_packet_timestamp = current_time_stamp

		flow_.total_size_taken += len(pkt_data)

		flow_.packet_size.append(len(pkt_data))

		if(protocol=="TCP"):
			if (isinstance(tcp_pkt.payload, NoPayload)):
				flow_.null_packets += 1
				is_null_packet = True
			else:
				current_payload = len(tcp_pkt.payload)
				flow_.tcp_payload += len(tcp_pkt.payload)
		elif(protocol=="UDP"):
			if (isinstance(udp_pkt.payload, NoPayload)):
				flow_.null_packets += 1
				is_null_packet = True
			else:
				current_payload = len(udp_pkt.payload)
				flow_.udp_payload += len(udp_pkt.payload)

		if (not is_null_packet):
			if (is_sender) :
				flow_.sent_payload += current_payload
			if (is_receiver):
				flow_.received_payload += current_payload

			if (len(ether_pkt) < flow_.SMALL_PACKET_THRESHOLD):
				flow_.small_packets += 1
		
		# ip_pair = combine_src_dst(src_ip, dst_ip)

		# assert(dport <= PORT_MASK)
		# port_pair = (sport << PORT_LEN) | dport



		# if (ip_pair not in pkt_dict):
		# 	pkt_dict[ip_pair] = Features()

		# pkt_dict[ip_pair].count += 1

		# pkt_dict[ip_pair].add_port_pair(port_pair)
		# pkt_dict[ip_pair].add_protocol(ether_pkt.proto)

		flow_.packet_length.append(pkt_metadata.wirelen)
		
		flow_.count += 1
		

	

	
	file_size =float (os.stat(file_path).st_size) / float(1024 * 1024)
	time_taken =float(time.process_time() - start)
	print ("File Size:",file_size, "MB")
	print("Time taken", time_taken)
	print ("Speed:",file_size / time_taken, "MB/s")
	# print ("PCAP size:", total_size_taken)
	# print (total_size_taken / file_size)
	# print ("NULL: ", null_packets)
	# print ("Unknown protocols:", other_protocol)
	# print (len(pkt_dict))
	# print (count)
	# print (first_packet_length)
	# print(total_duration)

	
	# print (average_packet_length, len(packet_length))
	# print (average_packet_ps)

def generate_features_dataset(file_path):

	
	flows_dict = {}

	ips_dict = {}
		
		
	generate_connections(file_path, flows_dict)
	num_of_flows = 0
	for key in flows_dict:
		if(flows_dict[key].src_ip not in ips_dict):
			ips_dict[flows_dict[key].src_ip] = 1
		if(flows_dict[key].total_num_packets>1):
			num_of_flows+=1
			features_list = flows_dict[key].get_features()
			csv_filename = CSV_FILENAME
			with open(csv_filename, "a") as fp:
				wr = csv.writer(fp, dialect='excel')
				wr.writerow(features_list)

	return ips_dict
			
def panda_dataframa_and_cleaning(csv_path):
	frame = pd.read_csv(csv_path, index_col=None, header=None)
	csv_columns = ['src_ip', 'dst_ip', 'sport', 'dport', 'protocol', 'total_pkts', 'null_pkts', 'small_pkts', 'percent_of_sml_pkts', 'ratio_incoming_outgoing', 'total_duration',  'average_payload', 'average_payload_sent', 'average_payload_receive', 'stddev_packet_length', 'freq_packet_length', 'payload_per_sec', 'avg_inter_times', 'avg_sent_inter_times', 'avg_rec_inter_times', 'med_inter_times', 'med_sent_inter_times', 'med_rec_inter_times', 'var_packet_size', 'var_packet_size_rec', 'var_packet_size_sent', 'max_packet_size', 'average_packet_length', 'first_packet_length', 'average_packet_ps']
	frame.columns = csv_columns
	frame = frame[frame['sport'] > 1000]
	frame = frame[frame['total_pkts'] > 2]

	frame.drop(['avg_sent_inter_times', 'avg_rec_inter_times', 'med_sent_inter_times', 'med_rec_inter_times', 'var_packet_size_rec', 'var_packet_size_sent'], axis=1, inplace=True)
	label_encoder = pk.load(open(osp.join("Models", "label_encoder.pkl"),'rb'))
	frame['protocol'] = label_encoder.transform(frame['protocol'])
	
	list_of_src_ip = frame['src_ip']
	list_of_dst_ip = frame['dst_ip']

	frame.drop(['src_ip', 'dst_ip'], axis=1, inplace=True)
	frame['var_packet_size'] = pd.to_numeric(frame['var_packet_size'], errors='coerce')
	frame = frame[frame['var_packet_size'].notna()]
	frame.astype('float64')

	test_data = frame.values

	return test_data, list_of_src_ip, list_of_dst_ip, frame

def predict(features):

	features = np.array(features, dtype=float)
	mms = pk.load(open(osp.join("Models", "mms.pkl"),'rb'))
	if not hasattr(mms, "clip"):
		# Backward compatibility for scalers pickled with older sklearn versions.
		mms.clip = False
	features = mms.transform(features)

	cluster = pk.load(open(osp.join("Models", "cluster.pkl"),'rb'))
	if not hasattr(cluster, "_n_threads"):
		# Backward compatibility for KMeans models pickled with older sklearn versions.
		cluster._n_threads = 1
	cluster_labels = cluster.predict(features)

	try:
		clf = load(osp.join('Models', 'flow_predictor.joblib'))
		model_labels = clf.predict(features)
	except Exception as ex:
		# Fallback when legacy joblib models are incompatible with current sklearn.
		print("Warning: flow_predictor.joblib is incompatible with current sklearn. "
			  "Using cluster-only prediction fallback. Details:", ex)
		model_labels = np.zeros(len(cluster_labels), dtype=int)

	labels = []

	for i in range(len(cluster_labels)):
		if(cluster_labels[i]==1 or cluster_labels[i]==2 or cluster_labels[i]==5 or cluster_labels[i]==8):
			labels.append(0)
		elif(cluster_labels[i]==6):
			labels.append(1)
		else:
			labels.append(model_labels[i])
	return labels

def results(labels, dict):
	result = []
	for i in labels:
		result.append(dict[i])
	return result

def write_text_file(ip_list, pred, all_ips_dict):
	d = {}

	for i in range(len(ip_list)):
		src = ip_list[i]
		if (src not in d):
			d[src] = []
		d[src].append(pred[i])

	text_file = open(TXT_FILENAME, "w+")
	text_file.close()

	text_file = open(TXT_FILENAME, "a")
	
	for ips in d:
		result_ = d[ips]
		percentage = sum(result_)/len(result_)
		if(percentage*100<5):
			text_file.write(ips + " , " + Benign_class_name + "\n")
		else:
			text_file.write(ips + " , " + Botnet_class_name + "\n")

	for ips in all_ips_dict:
		if(ips not in d):
			text_file.write(ips + " , " + Benign_class_name + "\n")
			
	text_file.close()

pred_to_result = {0:Benign_class_name,1:Botnet_class_name}

# Refresh CSV
with open(CSV_FILENAME, "w+") as fp:
				wr = csv.writer(fp, dialect='excel')

all_ips_dict = generate_features_dataset(file_path)

features, src_ip_list, dst_ip_list, dataframe = panda_dataframa_and_cleaning(CSV_FILENAME)

pred = predict(features)
labelled_pred = results(pred, pred_to_result)

dataframe['src_ip'] = src_ip_list
dataframe['dst_ip'] = dst_ip_list
dataframe['label'] = labelled_pred
dataframe = dataframe.reindex(sorted(dataframe.columns), axis=1)
dataframe.to_csv(CSV_FILENAME, index=False)

write_text_file(src_ip_list.values, pred, all_ips_dict)






