import os, time
import numpy
from scapy.utils import RawPcapReader
from scapy.layers.l2 import Ether
from scapy.layers.inet import IP, TCP, UDP
from scapy.packet import NoPayload
import csv
from scipy import stats
import natsort

root_directory = os.getcwd() + os.sep


def is_ip_file(filename):
	return (filename.lower().find("ip") >= 0)

def is_ds_store(filename):
	return (filename.lower().find("ds_store")>=0)


def generate_pcap_path_list(directory):

	ans = []
	add_file = False
	for filename in os.listdir(directory):
		if (not os.path.isdir(directory + filename)):
			if (not is_ip_file(filename) and not is_ds_store(filename)):
				add_file = True
			continue
		ans += generate_pcap_path_list(directory + filename + os.sep)

	if (add_file):
		ans.append(directory)
	return ans

def generate_ip_path_list(directory):
	ans = []
	add_file = False
	for filename in os.listdir(directory):
		if (not os.path.isdir(directory + filename)):
			if (is_ip_file(filename)):
				add_file = True
			continue
		ans += generate_ip_path_list(directory + filename + os.sep)

	if (add_file):
		ans.append(directory)
	return ans


def combine_src_dst(src,dst):
	return src + "_" + dst



def add_to_dict(key, sample_dict):
	if (key not in sample_dict):
		sample_dict[key] = 1
	else:
		sample_dict[key] += 1

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
		percent_of_small_packets = float(self.small_packets * 100) / float(self.total_num_packets)


		stddev_packet_length = numpy.std(self.packet_length)
		freq_packet_length = stats.mode(self.packet_length)[1][0]
		avg_inter_times = numpy.mean(self.inter_arrival_times)
		avg_sent_inter_times = numpy.mean(self.inter_arrival_times_send)
		avg_rec_inter_times = numpy.mean(self.inter_arrival_times_receive)

		med_inter_times = numpy.median(self.inter_arrival_times)
		med_sent_inter_times = numpy.median(self.inter_arrival_times_send)
		med_rec_inter_times = numpy.median(self.inter_arrival_times_receive)


		var_packet_size = numpy.var(self.packet_size)
		var_packet_size_sent = numpy.var(self.packet_size_sent)
		var_packet_size_rec = numpy.var(self.packet_size_receive)

		max_packet_size = max(self.packet_size)
		# Reconnection , total number of bytes --  is this file size?, 
		# average bits/s =  total payload / total duration ?
		file_feature_list_1 = [self.total_num_packets, self.null_packets, self.small_packets, percent_of_small_packets, ratio_of_incoming_to_outgoing, self.total_duration,  average_payload, average_payload_sent, average_payload_receive]
		file_feature_list_2 = [stddev_packet_length, float(freq_packet_length) / float(self.count), float(total_payload)/float(self.total_duration), avg_inter_times, avg_sent_inter_times, avg_rec_inter_times]
		file_feature_list_3 = [med_inter_times, med_sent_inter_times, med_rec_inter_times, var_packet_size, var_packet_size_rec,var_packet_size_sent, max_packet_size]

		# this was in first paper

		average_packet_length = numpy.mean(self.packet_length)
		first_packet_length = self.packet_length[0]
		average_packet_ps = float(self.count * self.MICROSECOND) / float(self.total_duration)
		file_feature_list_4 = [average_packet_length, first_packet_length, average_packet_ps]

		file_features = [self.src_ip, self.dst_ip, self.sport, self.dport, self.protocol]

		file_features += file_feature_list_1 + file_feature_list_2 + file_feature_list_3 + file_feature_list_4
		print ("Packets processed: ", self.total_num_packets)
		print ("Number of features: ", len(file_features))

		return file_features



PORT_LEN = 16
PORT_MASK = (1 << PORT_LEN) - 1

def get_back_port_pair(port_mask):

	return (port_mask >> PORT_LEN, port_mask & (PORT_MASK))


def expand(x):
    yield x
    while x.payload:
        x = x.payload
        yield x

def get_layer_list(x):
	return list(expand(x))

def generate_connections(path, filename, ip_addr, flows_dict):

	start = time.process_time()

	print ("generating features for:", path + filename,"with ips:",ip_addr)

	other_protocol = 0


	MICROSECOND = 10**6


	for (pkt_data, pkt_metadata) in RawPcapReader(path + filename):

		# if 'usec' not in pkt_metadata:
		# 	continue


		ether_pkt = Ether(pkt_data)

		if 'type' not in ether_pkt.fields:
			continue

		if ether_pkt.type != 0x0800:
			assert (ether_pkt.type == 2054)
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

		key_ = str(src_ip) + str(dst_ip) + str(sport) + str(dport) + str(protocol)

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
			assert(current_time_stamp > flow_.last_packet_timestamp)
		
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
		

	

	
	file_size =float (os.stat(path + filename).st_size) / float(1024 * 1024)
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



def get_ip_details(path):
	path = path[:len(path) - 1]
	folder_name = os.path.basename(path)	
	folder_name = folder_name.replace('_','')
	dir_path = os.path.dirname(path) + os.sep
	ans = []

	for filename in os.listdir(dir_path):
		if (not os.path.isdir(dir_path +  filename)) and (is_ip_file(filename)):
			if (filename.lower().find(folder_name) >= 0):
				file = open(dir_path + filename, "r")

				res = []
				lines = file.readlines()
				for line in lines:
					words = line.split()
					for word in words:
						ans.append(word)
				file.close()
			else:
				file = open(dir_path + filename, "r")
				lines = file.readlines()

				for line in lines:
					line = line.lower()
					line = line.replace('_','')
					if (line.lower().find(folder_name) >= 0):
						words = line.split()
						for word in words:
							if (word.lower().find(folder_name) >= 0):
								continue
							ans.append(word)
	res = set(ans)
	ans = [ip for ip in res]
	return ans, folder_name


def generate_features_dataset(directory):
	start = time.process_time()
	pcap_list = generate_pcap_path_list(directory)
	ip_list = generate_ip_path_list(directory)

	count_iter = 0

	for path in pcap_list:
		curr_ip_details, folder_name = get_ip_details(path)
		print ("IP:",curr_ip_details,"for path",path)
		list_dir = os.listdir(path)
		list_dir = natsort.natsorted(list_dir)
		flows_dict = {}
		for filename in list_dir:
			assert( not is_ip_file(filename) )

			if(filename.find('.csv')>=0 or is_ds_store(filename)):
				continue

			generate_connections(path, filename, curr_ip_details, flows_dict)
		num_of_flows = 0
		for key in flows_dict:
			if(flows_dict[key].src_ip in curr_ip_details and flows_dict[key].total_num_packets>1):
				num_of_flows+=1
				features_list = flows_dict[key].get_features()
				csv_filename = folder_name + ".csv"
				with open(path + csv_filename, "a") as fp:
					wr = csv.writer(fp, dialect='excel')
					wr.writerow(features_list)
		print("Number of flows", num_of_flows)
			
	print("Total Time Taken:",time.process_time() - start)

generate_features_dataset(root_directory + "Botnet_Detection_Dataset" + os.sep  + "Botnet" + os.sep + "torrent" + os.sep)

