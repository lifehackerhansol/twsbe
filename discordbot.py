import discord
import requests
import os
import datetime

from cleaninty.ctr.simpledevice import SimpleCtrDevice
from cleaninty.ctr.soap.manager import CtrSoapManager
from cleaninty.ctr.soap import helpers, ias


def checkReg(console):
    device = SimpleCtrDevice(json_file=console)
    soap_device = CtrSoapManager(device, False)
    helpers.CtrSoapCheckRegister(soap_device)
    device.serialize_json(json_file=console)
    print(f"region: {soap_device.region} country: {soap_device.country}")
    return [soap_device.country, soap_device.region]

def _run_unregister(device, soap_device):
	try:
		ias.Unregister(soap_device, ias.GetChallenge(soap_device).challenge)
		soap_device.unregister_account()
		virtual = False
	except SoapCodeError as e:
		if e.soaperrorcode != 434:
			raise
		virtual = True

	if virtual:
		print("Virtual account link! Attempt detach by error...")
		device.reboot()

		print("Initializing console session...")
		helpers.CtrSoapUseSystemApps(soap_device, helpers.SysApps.SYSTRANSFER)
		helpers.CtrSoapSessionConnect(soap_device)

		device_ninja = NinjaManager(soap_device)
		try:
			device_ninja.open_without_nna()
		except NinjaException as e:
			if e.errorcode != 3136:
				raise

		device.reboot()

		print("Initializing console...")
		helpers.CtrSoapUseSystemApps(soap_device, helpers.SysApps.ESHOP)

		print("Checking registry...")
		helpers.CtrSoapCheckRegister(soap_device)

		if soap_device.account_status != 'U':
			print("Unregister...")
			ias.Unregister(soap_device, ias.GetChallenge(soap_device).challenge)
			soap_device.unregister_account()
		else:
			print("Unregistered!")

def EShopRegionChange(console, region, country):
    print("Initializing console...")
    device = SimpleCtrDevice(json_file=console)
    soap_device = CtrSoapManager(device, False)

    print("Checking registry...")
    helpers.CtrSoapCheckRegister(soap_device)

    print("Saving updated session...")
    device.serialize_json(json_file=console)

    # if region == soap_device.region and soap_device.account_status != 'U': impossible
    #	print("Console already in the desired region.")
    #	return

    device.reboot()

    if soap_device.account_status != 'U':
        print("Initializing console session...")
        helpers.CtrSoapUseSystemApps(soap_device, helpers.SysApps.ESHOP)
        helpers.CtrSoapSessionConnect(soap_device)  

        print("Saving updated session...")
        device.serialize_json(json_file=console)    

        print("Unregister...")
        _run_unregister(device, soap_device)

        print("Saving updated session...")
        device.serialize_json(json_file=console)

        device.reboot()

    soap_device.region_change(region, country, None)

    print("Initializing console session...")
    helpers.CtrSoapUseSystemApps(soap_device, helpers.SysApps.ESHOP)
    try:
        helpers.CtrSoapSessionConnect(soap_device)
    except SoapCodeError as e:
        if e.soaperrorcode == 602:
            return 1
        return e.soaperrorcode

    print("Saving updated session...")
    device.serialize_json(json_file=console)

    print("Complete!")
    return 0

def _move_account(source_console, target_console):
	print("Initializing source console...")
	source = SimpleCtrDevice(json_file=source_console)
	soap_source = CtrSoapManager(source, False)

	print("Initializing target console...")
	target = SimpleCtrDevice(json_file=target_console)
	soap_target = CtrSoapManager(target, False)

	helpers.CtrSoapUseSystemApps(soap_source, helpers.SysApps.SYSTRANSFER)
	helpers.CtrSoapUseSystemApps(soap_target, helpers.SysApps.SYSTRANSFER)

	print("Initializing console sessions...")
	helpers.CtrSoapSessionConnect(soap_source)
	helpers.CtrSoapSessionConnect(soap_target)

	print("Saving updated sessions...")
	source.serialize_json(json_file=source)
	target.serialize_json(json_file=target)

	print("Checking if we can move account...")
	movestatus = ias.MoveAccount(
		soap_source,
		soap_target.device_id,
		soap_target.account_id,
		soap_target.st_token,
		True
	)

	print("Performing move...")
	movestatus = ias.MoveAccount(
		soap_source,
		soap_target.device_id,
		soap_target.account_id,
		soap_target.st_token,
		False
	)

	print("Complete!")

def _del_eshop(console):
	print("Initializing console...")
	device = SimpleCtrDevice(json_file=console)
	soap_device = CtrSoapManager(device, False)

	print("Checking registry...")
	helpers.CtrSoapCheckRegister(soap_device)

	print("Saving updated session...")
	device.serialize_json(console)

	if soap_device.account_status == 'U':
		print("Console already does not have EShop account.")
		return

	device.reboot()

	print("Initializing console session...")
	helpers.CtrSoapUseSystemApps(soap_device, helpers.SysApps.ESHOP)
	helpers.CtrSoapSessionConnect(soap_device)

	print("Saving updated session...")
	device.serialize_json(json_file=console)

	print("Unregister...")
	_run_unregister(device, soap_device)

	print("Saving updated session...")
	device.serialize_json(json_file=console)

	print("Complete!")

def checkSerialblacklist(serial):
    with open("serialblacklist.txt", "r") as f:
        for x in f:
            if serial == x:
                return True

def validSerial(serial, checkdigit):
    if not checkdigit:
        if checkSerialblacklist(serial):
            return 2
        return 0
    else:
        if checkSerialblacklist(serial[(len(serial)-1):]):
            return 2
        if serial[2].isdigit():
            serialtocheck = serial[2:]
        elif serial[3].isdigit():
            serialtocheck = serial[3:]
        else: 
            return 1
        odds = int(serialtocheck[0])+int(serialtocheck[2])+int(serialtocheck[4])+int(serialtocheck[6])
        evens = int(serialtocheck[1])+int(serialtocheck[3])+int(serialtocheck[5])+int(serialtocheck[7])
        checkdigit = ((3 * evens) + odds) % 10
        if checkdigit != 0:
            checkdigit = 10 - checkdigit
        if int(serialtocheck[8]) == checkdigit:
            return 0
        else: 
            return 1

def getCountry(region):
    # random country from serial region 
    if region in ['E', 'A']: #europe (EA SPORTS WTF???)
        return "GB"
    if region in ['S', 'B', 'W']: #north america (SBW OMG ITS SUBWAY???)
        return "US"
    if region == 'J':
        return "JP"
    if region == 'K':
        return "KR"
    if region == 'C':
        return "CN"
    if region == 'T':
        return "HK"
    return 0

def cleanup():
    try:
        os.remove("essential.exefs")
    except Exception:
        pass
    try:
        os.remove("otp.bin")
    except Exception:
        pass

def getDonorCooldown(console):
    device = SimpleCtrDevice(json_file=console)
    soap_device = CtrSoapManager(device, False)

    helpers.CtrSoapCheckRegister(soap_device)

    device.serialize_json(json_file=console)

    acct_attributes = ias.GetAccountAttributesByProfile(soap_device, 'MOVE_ACCT')

    moved_times = None
    moved_last_time = None

    for i in acct_attributes.accountattributes:
        if   i[0] == 'MoveAccountTimes':
            moved_times = int(i[1]) if i[1] else 0
        elif i[0] == 'MoveAccountLastMovedDate':
            moved_last_time = int(i[1]) if i[1] else 0

    utc_0 = datetime.datetime.utcfromtimestamp(0)

    server_time = utc_0 + datetime.timedelta(milliseconds=acct_attributes.timestamp)
    if moved_last_time is not None:
        moved_last_time = utc_0 + datetime.timedelta(milliseconds=moved_last_time)
        time_ready_for_new_move = moved_last_time + datetime.timedelta(days=7)

    return moved_last_time.strftime("%Y-%b-%d")

def initDatabase():
    seekcount = 0
    donors = os.listdir('./donors/')
    print("Initializing donors...")
    db = open("db.txt", "w")
    for i in range(len(donors)):
        lastmoved = getDonorCooldown(f"donors/{donors[i]}")
        donorentry = f"{donors[i]} {lastmoved}\n"
        db.seek(seekcount)
        db.write(donorentry)
        seekcount = seekcount + len(donorentry)
    db.close()
    print("Done!")

def getReadyDonor():
    db = open("db.txt", "r")
    content = db.read()
    donors = content.splitlines()
    for i in range(len(donors)):
        donorlastmoved = donors[i].split()[1]
        currenttime = datetime.datetime.now().strftime("%Y-%b-%d")
        if currenttime - datetime.timedelta(days=7) > donorlastmoved:
            return f"donors/{donors[i]}"
         
def updateDonor(donor):
    offset = 0
    db = open("db.txt", "r") # find donor
    content = db.read()
    donors = content.splitlines()
    for i in range(len(donors)):
        curdonor = donors[i].split()[1]
        if donor == curdonor:
            offset = offset + len(donors[i].split()[0])+1
            db = open("db.txt", "w")
            db.seek(offset)
            db.write(getDonorCooldown(f"donors/{donors[i]}"))
            db.close()
            return
        offset = offset + len(donors[i])+1
    
def confirmCountryMatch(target, donor):
    donorlocale = CheckReg(donor)
    targetlocale = CheckReg(target)
    if targetlocale != donorlocale:
        _del_eshop(donor)
        erchangeresult = EShopRegionChange(donor, targetlocale[1], targetlocale[0])
        
        if erchangeresult == 0:
            return 0
        else:
            print(f"EShopRegionChange on donor failed. Make sure you put a fixed donor inside. Faulty donor: {donor} Soap error if not 1: {erchangeresult}")
            return 1
        
    


intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

@client.event
async def on_ready(): 
    print(f"Good Morning, {client.user} here")

@client.event
async def on_message(message):
    if message.author == client.user:
        return
    if message.content.startswith('-soap'):
        ignoreserialgiven = False
        useotp = False
        ignoresecinfoserial = False
        print(message.content)
        argv = message.content.split()
        if len(argv) == 1: 
            return
        if argv[1] == "--help": 
            await message.channel.send('usage: -soap <link to essential> <serial>\nspecial: \n-soap <link to essential> --force | ignores given serial\n-soap <link to otp> <serial> --otp | uses otp instead of essential')
            return
        if not argv[1].startswith('https'):
            await message.channel.send('invalid syntax :(')
            return
        if validSerial(argv[2], True) == 1:
            await message.channel.send(f'invalid serial: {argv[2]}')
            return
        elif validSerial(argv[2], True) == 2:
            await message.channel.send(f'blacklisted serial(maybe lazed?): {argv[2]}')
            return
        elif argv[2] == "--force":
            ignoreserialgiven = True
        if len(argv) == 4:
            if argv[3] == "--otp":
                ignoresecinfoserial = True
                useotp = True
        download = requests.get(argv[1])
        if download.status_code != 200:
            await message.channel.send(f"Bad link, returned {download.status_code}")
            return
        if not useotp:
            essentialfp = open("essential.exefs", 'wb')
            essentialfp.write(essential.content)
            exefs = ExeFSReader(essentialfp)
            otp = exefs.open("otp.bin")
            secinfo = exefs.open("secinfo.bin")
            essentialfp.close()
        else: 
            otp = open("otp.bin", "wb")
            otp.write(download.content)
        if not ignoresecinfoserial:
            secinfo.seek(102)
            secinfoserial = secinfo.read(0xF).decode("ascii")
            secinfo.seek(0)
            if argv[2][(len(argv[2])-1):] != secinfoserial and not ignoreserialgiven:
                await message.channel.send(f"Serials dont match! {argv[2][(len(argv[2])-1):]} not {secinfoserial}")
                cleanup()
                return
            if ignoreserialgiven:
                if validSerial(secinfoserial, False) == 2:
                    await message.channel.send(f"blacklisted serial")
                    cleanup()
                    return
            genjsoncountry = getCountry(argv[2][1])
            if genjsoncountry == 0:
                await message.channel.send(f"unknown serial: {argv[2]}")
                cleanup()
                return
            progress = "[ ]Generated JSON\n[ ]CheckReg Success\n[ ]EShopRegionChange\n[ ]SysTransfer"
            progressmessage = await message.channel.send("[ ]Generated JSON\n[ ]CheckReg\n[ ]EShopRegionChange\n[ ]SysTransfer")
            donorjson = open("console.json", "w")
            SimpleCtrDevice.generate_new_json(otp_fp=otp, secureinfo_fp=secinfo, country=genjsoncountry, json_file="console.json")
            otp.close()
            secinfo.close()
        else:
            genjsoncountry = getCountry(argv[2][1]) 
            if validSerial(argv[2], True) == 2:
                await message.channel.send(f"blacklisted serial")
                cleanup()
                return
            if validSerial(argv[2], True) == 1:
                await message.channel.send(f'invalid serial: {argv[2]}')
                return
            progress = "[ ]Generated JSON\n[ ]CheckReg Success\n[ ]EShopRegionChange\n[ ]SysTransfer"
            progressmessage = await message.channel.send("[ ]Generated JSON\n[ ]CheckReg\n[ ]EShopRegionChange\n[ ]SysTransfer")
            donorjson = open("console.json", "w")
            SimpleCtrDevice.generate_new_json(otp_fp=otp, serialnumber=argv[2], country=genjsoncountry, json_file="console.json")
            otp.close()
            
        progress.replace("[ ]G", "[S]G")
        await progressmessage.edit(progress)
        checkregresult = CheckReg("console.json")
        if checkregresult[1] != "USA":
            erchangeresult = EShopRegionChange("console.json", "USA", "US")
        else:
            erchangeresult = EShopRegionChange("console.json", "EUR", "GB")
        if erchangeresult == 0:
            progress.replace("[ ]E", "[S]E")
            print("EShopRegionChange success!")
            progress.replace("[ ]S", "[-]S")
            await progressmessage.edit(progress)
            await message.channel.send("Done! Make sure that the country in System Settings -> Other Settings -> Profile is set to new region and country, then try eShop!")
        elif erchangeresult != 1:
            progress.replace("[ ]E", "[S]E")
            print("EShopRegionChange success!")
            await progressmessage.edit(progress)
        else:
            progress.replace("[ ]E", "[F]E")
            print(f"EShopRegionChange failure! Soap error code: {erchangeresult}")
            cleanup()
            return
        thedonor = getReadyDonor()
        confirmCountryMatch("console.json", thedonor)
        systransferresult = _move_account("console.json", thedonor)
        if systransferresult == 0:
            progress.replace("[ ]S", "[S]S")
            print("SysTransfer success")
            await progressmessage.edit(progress)
            await message.channel.send("Done! Make sure that the country in System Settings -> Other Settings -> Profile is set to new region and country, then try eShop!")
            cleanup()
        else:
            progress.replace("[ ]S", "[F]S")
            print("SysTransfer failure")
            await progressmessage.edit(progress)
            cleanup()
            return
        updateDonor(thedonor)
        return
    
initDatabase()
client.run("token here")