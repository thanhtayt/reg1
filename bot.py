availabilityDomains = ["IEcv:AP-SINGAPORE-1-AD-1"]
displayName = 'instance-20230916-0556'
compartmentId = 'ocid1.tenancy.oc1..aaaaaaaaarpbdoaplvmbxsjypoyrrprx2o6kyghsi5tmvzjl722tvydmsblq&availabilityDomain=IEcv%3AAP-SINGAPORE-1-AD-1'
subnetId = 'ocid1.subnet.oc1.ap-singapore-1.aaaaaaaa3fphab4w3viavzg36vkkiz4momb5jlttkqxdq4xdbfvymdjngjda'
ssh_authorized_keys = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAILyJvzn9aKJvyMGKw3Kfzd1Zd9XJIq6FicPKKnGi0+ZT"

imageId = "ocid1.image.oc1.ap-singapore-1.aaaaaaaakn4ccqsr32n4aeppwkcd6fzcq2bcy6wvpsuqw3zzrk5tcx3ol67a"
boot_volume_size_in_gbs="xxx"
boot_volume_id="xxxx"

bot_token = "6568832406:AAHQEjcZBqhLbneiX-KZ-G1tlG0uDfXDLw0"
uid = "6191745507"

ocpus = 1
memory_in_gbs = 1

import oci
import logging
import time
import sys
import telebot

bot = telebot.TeleBot(bot_token)

LOG_FORMAT = '[%(levelname)s] %(asctime)s - %(message)s'
logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    handlers=[
        logging.FileHandler("oci.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

logging.info("#####################################################")
logging.info("Script to spawn VM.Standard.E2.1.Micro instance")


message = f'Start spawning instance VM.Standard.E2.1.Micro - {ocpus} ocpus - {memory_in_gbs} GB'
logging.info(message)

logging.info("Loading OCI config")
config = oci.config.from_file(file_location="./config")

logging.info("Initialize service client with default config file")
to_launch_instance = oci.core.ComputeClient(config)

message = f"Instance to create: VM.Standard.E2.1.Micro - {ocpus} ocpus - {memory_in_gbs} GB"
logging.info(message)

volume_client = oci.core.BlockstorageClient(config)

total_volume_size=0

logging.info("Check available storage in account")

if imageId!="xxxx":
	try:
		list_volumes = volume_client.list_volumes(compartment_id=compartmentId).data
	except Exception as e:
		logging.info(f"{e}")
		logging.info("Error detected. Stopping script. Check bot.py file, config file and oci_private_key.pem file. If you can't fix error, contact me.")
		sys.exit()
	if list_volumes!=[]:
		for block_volume in list_volumes:
			if block_volume.lifecycle_state not in ("TERMINATING", "TERMINATED"):
				total_volume_size=total_volume_size+block_volume.size_in_gbs
	for availabilityDomain in availabilityDomains:
		list_boot_volumes = volume_client.list_boot_volumes(availability_domain=availabilityDomain,compartment_id=compartmentId).data
		if list_boot_volumes!=[]:
			for b_volume in list_boot_volumes:
				if b_volume.lifecycle_state not in ("TERMINATING", "TERMINATED"):
					total_volume_size=total_volume_size+b_volume.size_in_gbs
	free_storage=200-total_volume_size
	if boot_volume_size_in_gbs!="xxxx" and free_storage<boot_volume_size_in_gbs:
		logging.critical(f"There is {free_storage} GB out of 200 GB left in your oracle cloud account. {boot_volume_size_in_gbs} GB storage needs to create this vps. So, you need to delete unnecessary boot and block volumes in your oracle cloud account. **SCRIPT STOPPED**")
		sys.exit()
	if boot_volume_size_in_gbs=="xxxx" and free_storage<47:
		logging.critical(f"There is {free_storage} GB out of 200 GB left in your oracle cloud account. 47 GB storage needs to create this vps. So, you need to delete unnecessary boot and block volumes in your oracle cloud account. **SCRIPT STOPPED**")
		sys.exit()
		
logging.info("Check current instances in account")

try:
	current_instance = to_launch_instance.list_instances(compartment_id=compartmentId)
except Exception as e:
	logging.info(f"{e}")
	logging.info("Error detected. Stopping script. Check bot.py file, config file and oci_private_key.pem file. If you can't fix error, contact me.")
	sys.exit()

response = current_instance.data

total_ocpus = total_memory = _A1_Flex = 0
instance_names = []

if response:
	logging.info(f"{len(response)} instance(s) found!")
	for instance in response:
		logging.info(f"{instance.display_name} - {instance.shape} - {int(instance.shape_config.ocpus)} ocpu(s) - {instance.shape_config.memory_in_gbs} GB(s) | State: {instance.lifecycle_state}")
		instance_names.append(instance.display_name)
		if instance.shape == "VM.Standard.E2.1.Micro" and instance.lifecycle_state not in ("TERMINATING", "TERMINATED"):
			_A1_Flex += 1
			total_ocpus += int(instance.shape_config.ocpus)
			total_memory += int(instance.shape_config.memory_in_gbs)
	message = f"Current: {_A1_Flex} active VM.Standard.E2.1.Micro instance(s) (including RUNNING OR STOPPED)"
	logging.info(message)
else:
	logging.info(f"No instance(s) found!")
	
message = f"Total ocpus: {total_ocpus} - Total memory: {total_memory} (GB) || Free {2-total_ocpus} ocpus - Free memory: {2-total_memory} (GB)"
logging.info(message)

if total_ocpus + ocpus > 2 or total_memory + memory_in_gbs > 2:
	message = "Total maximum resource exceed free tier limit (Over 2 AMD micro instances total). **SCRIPT STOPPED**"
	logging.critical(message)
	sys.exit()
	
if displayName in instance_names:
	message = f"Duplicate display name: >>>{displayName}<<< Change this! **SCRIPT STOPPED**"
	logging.critical(message)
	sys.exit()
	
message = f"Precheck pass! Create new instance VM.Standard.E2.1.Micro: {ocpus} opus - {memory_in_gbs} GB"
logging.info(message)

wait_s_for_retry = 10
tc=0
oc=0

if imageId!="xxxx":
	if boot_volume_size_in_gbs=="xxxx":
		op=oci.core.models.InstanceSourceViaImageDetails(source_type="image", image_id=imageId)
	else:
		op=oci.core.models.InstanceSourceViaImageDetails(source_type="image", image_id=imageId,boot_volume_size_in_gbs=boot_volume_size_in_gbs)
	
if boot_volume_id!="xxxx":
	op=oci.core.models.InstanceSourceViaBootVolumeDetails(source_type="bootVolume", boot_volume_id=boot_volume_id)
	
while True:
	for availabilityDomain in availabilityDomains:
		instance_detail = oci.core.models.LaunchInstanceDetails(metadata={"ssh_authorized_keys": ssh_authorized_keys},availability_domain=availabilityDomain,shape='VM.Standard.E2.1.Micro',compartment_id=compartmentId,display_name=displayName,source_details=op,create_vnic_details=oci.core.models.CreateVnicDetails(assign_public_ip=False, subnet_id=subnetId, assign_private_dns_record=True),agent_config=oci.core.models.LaunchInstanceAgentConfigDetails(is_monitoring_disabled=False,is_management_disabled=False,plugins_config=[oci.core.models.InstanceAgentPluginConfigDetails(name='Vulnerability Scanning', desired_state='DISABLED'), oci.core.models.InstanceAgentPluginConfigDetails(name='Compute Instance Monitoring', desired_state='ENABLED'), oci.core.models.InstanceAgentPluginConfigDetails(name='Bastion', desired_state='DISABLED')]),defined_tags={},freeform_tags={},instance_options=oci.core.models.InstanceOptions(are_legacy_imds_endpoints_disabled=False),availability_config=oci.core.models.LaunchInstanceAvailabilityConfigDetails(recovery_action="RESTORE_INSTANCE"),shape_config=oci.core.models.LaunchInstanceShapeConfigDetails(ocpus=ocpus, memory_in_gbs=memory_in_gbs))
		try:
			to_launch_instance.launch_instance(instance_detail)
			message = 'VPS is created successfully! Watch video to get public ip address for your VPS'
			logging.info(message)
			if bot_token!="xxxx" and uid!="xxxx":
				while True:
					try:
						bot.send_message(uid, message)
						break
					except:
						time.sleep(5)
			sys.exit()
		except oci.exceptions.ServiceError as e:
			if oc==2:
				wait_s_for_retry=wait_s_for_retry-1
				oc=0
			if tc==2:
				wait_s_for_retry=wait_s_for_retry+1
				tc=0
			if e.status == 500:
				tc=0
				if wait_s_for_retry>10:
					oc=oc+1
				message = f"{e.message}. Retrying after {wait_s_for_retry} seconds"
				logging.info(message)
				if bot_token!="xxxx" and uid!="xxxx":
					try:
						bot.send_message(uid, message)
					except:
						pass
				time.sleep(wait_s_for_retry)
			elif e.status == 429 or e.status == 400:
				oc=0
				tc=tc+1
				message = f'"Too Many Requests" error detected. Retrying after {wait_s_for_retry} seconds'
				logging.info(message)
				if bot_token!="xxxx" and uid!="xxxx":
					try:
						bot.send_message(uid, message)
					except:
						pass
				time.sleep(wait_s_for_retry)
			else:
				logging.info(f"{e}")
				message = f"Error detected. Stopping script. If you can't fix error, contact me"
				logging.info(message)
				if bot_token!="xxxx" and uid!="xxxx":
					try:
						bot.send_message(uid, message)
					except:
						pass
				sys.exit()
		except Exception as e:
			if tc==2:
				wait_s_for_retry=wait_s_for_retry+1
				tc=0
			if oc==2:
				wait_s_for_retry=wait_s_for_retry-1
				oc=0
			if "oracle" in str(e):
				oc=0
				tc=tc+1
				message = f'"Too Many Requests" error detected. Retrying after {wait_s_for_retry} seconds'
				logging.info(message)
				if bot_token!="xxxx" and uid!="xxxx":
					try:
						bot.send_message(uid, message)
					except:
						pass
				time.sleep(wait_s_for_retry)
			else:
				logging.info(f"{e}")
				message = f"Error detected. Stopping script. If you can't fix error, contact me"
				logging.info(message)
				if bot_token!="xxxx" and uid!="xxxx":
					try:
						bot.send_message(uid, message)
					except:
						pass
				sys.exit()
		except KeyboardInterrupt:
			sys.exit()