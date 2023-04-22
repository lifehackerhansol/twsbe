import discord
import requests
import subprocess
import os
import datetime

def validSerial(serial):
    f = open("serialblacklist.txt", "r")
    for x in f:
        if serial == x:
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
    os.removedirs("out")
    os.remove("essential.exefs")

def getDonorCooldown(donor):
    command = ["cleaninty", "ctr", "LastTransfer", "-C", f"donors/{donor}"]
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    if process.returncode != 0:
        print(f"faulty donor: {donors[i]}")
        print("exiting...")
        exit()
    v = stdout.splitlines()[4]
    print(f"donor {donor} {v.decode('utf-8')}")
    date = v.decode('utf-8').split()
    return datetime.datetime.strptime(f"{date[6]}-{date[5]}-{date[4]}", "%Y-%b-%d")

def initLastTransfersAndUpdateDonorDatabaseUpdatingTheStuffWithHeartToBeHappyWhenAllOfThisWorks():
    seekcount = 0
    donors = os.listdir('./donors/')
    print("Initializing donors...")
    db = open("db.txt", "w")
    for i in range(len(donors)):
        lastmoved = getDonorCooldown(donors[i])
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
            db.write(getDonorCooldown(donors[i]))
            db.close()
            return
        offset = offset + len(donors[i])+1
    
def confirmCountryMatch(target, donor):
    command = ["cleaninty", "ctr", "CheckReg", "-C", "donor"]
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    donormessage = stdout.decode('utf-8').splitlines()
    donorcountry = message[6].split()[3]
    command = ["cleaninty", "ctr", "CheckReg", "-C", target]
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    targetmessage = stdout.decode('utf-8').splitlines()
    targetregion = message[5].split()[3]
    targetcountry = message[6].split()[3]
    if targetcountry != donorcountry:
        command = ["cleaninty", "ctr", "EShopDelete", "-C", donor]
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        if not "Complete!" in stdout.decode('utf-8').split():
            print(f"EShopDelete of donor failed: { stdout.decode('utf-8') }\nFaulty donor: {donor}")
            return 1
        command = ["cleaninty", "ctr", "EShopRegionChange", "-C", donor, "-r", targetregion, "-c", targetcountry]
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        if "Complete!" in stdout.decode('utf-8').split():
            return 0
        else:
            print(f"EShopRegionChange on donor failed: {stdout.decode('utf-8')}\nMake sure you put a fixed donor inside. Faulty donor: {donor}")
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
        print(message.content)
        argv = message.content.split()
        if argv[1] == "--help": 
            await message.channel.send('usage: -soap <link to essential> <serial>')
            return
        if not argv[1].startswith('https'):
            await message.channel.send('invalid syntax :(')
            return
        if validSerial(argv[2]) == 1:
            await message.channel.send(f'invalid serial: {argv[2]}')
            return
        elif validSerial(argv[2]) == 2:
            await message.channel.send(f'blacklisted serial(maybe lazed?): {argv[2]}')
            return
        essential = requests.get(argv[1])
        if essential.status_code != 200:
            await message.channel.send(f"Bad link, returned {essential.status_code}")
            return
        open("essential.exefs", 'wb').write(essential.content)
        if not os.path.exists("out"):
            os.makedirs("out")
        command = ["ninfs", "exefs", "essential.exefs", "out"]
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        if process.returncode != 0:
            await message.channel.send(f"exefs mount fail: {stderr.decode('utf-8')}")
            cleanup()
            return
        else:
            print(f"mount exefs success: {stdout.decode('utf-8')}")
        secinfo = open("out/secinfo.bin", "rb")
        secinfo.seek(102)
        secinfoserial = secinfo.read(0xF).decode("ascii")
        if argv[2][(len(argv[2])-1):] != secinfoserial:
            await message.channel.send(f"Serials dont match! {argv[2][(len(argv[2])-1):]} not {secinfoserial}")
            cleanup()
            return
        genjsoncountry = getCountry(argv[2][1])
        if genjsoncountry == 0:
            await message.channel.send(f"unknown serial: {argv[2]}")
            cleanup()
            return
        command = ["cleaninty", "ctr", "GenJson", "--otp" "out/otp.bin", "--secureinfo", "secinfo.bin", "--country", genjsoncountry, "--out", "console.json"]
        progress = "[ ]Generated JSON\n[ ]CheckReg Success\n[ ]EShopRegionChange\n[ ]SysTransfer"
        progressmessage = await message.channel.send("[ ]Generated JSON\n[ ]CheckReg\n[ ]EShopRegionChange\n[ ]SysTransfer")
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        if process.returncode != 0:
            progress.replace("[ ]G", "[F]G")
            await progressmessage.edit(progress)
            print(f"genjson failure: {stderr.decode('utf-8')}")
            cleanup()
            return
        else:
            progress.replace("[ ]G", "[S]G")
            print(f"genjson success: {stdout.decode('utf-8')}")
        command = ["cleaninty", "ctr", "CheckReg", "-C", "console.json"]
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        if process.returncode != 0:
            progress.replace("[ ]C", "[F]C")
            await progressmessage.edit(progress)
            print(f"checkreg failure: {stderr.decode('utf-8')}")
            cleanup()
            return
        else:
            progress.replace("[ ]C", "[S]C")
            print(f"checkreg success: {stdout.decode('utf-8')}")
        if genjsoncountry != "US":
            command = ["cleaninty", "ctr", "EShopRegionChange", "-C", "console.json", "-r", "USA", "-c", "US"]
        else:
            command = ["cleaninty", "ctr", "EShopRegionChange", "-C", "console.json", "-r", "EUR", "-c", "GB"]
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        if "Complete!" in stdout.decode('utf-8').split():
            progress.replace("[ ]E", "[S]E")
            print(f"EShopRegionChange success: {stdout.decode('utf-8')}")
            progress.replace("[ ]S", "[-]S")
            await progressmessage.edit(progress)
            await message.channel.send("Done! Make sure that the country in System Settings -> Other Settings -> Profile is set to new region and country, then try eShop!")
            cleanup()
            return
        elif not ("602" in stderr.decode('utf-8').split() or "602" in stdout.decode('utf-8').split()): #dunno if it goes to stderr or stdout
            print(f"shit what happened{stdout.decode('utf-8')} & {stderr.decode('utf-8')}")
            await message.channel.send("Error while EShopRegionChange! Check logs for details")
            cleanup()
            return
        thedonor = f"donors/{getReadyDonor()}"
        confirmCountryMatch("console.json", thedonor)
        command = ["cleaninty", "ctr", "-s", "console.json", "-t", thedonor]
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        if "Complete!" in stdout.decode('utf-8').split():
            progress.replace("[ ]S", "[S]S")
            print(f"SysTransfer success: {stdout.decode('utf-8')}")
            await progressmessage.edit(progress)
            await message.channel.send("Done! Make sure that the country in System Settings -> Other Settings -> Profile is set to new region and country, then try eShop!")
            cleanup()
        else:
            progress.replace("[ ]S", "[F]S")
            print(f"SysTransfer failure: {stdout.decode('utf-8')}")
            await progressmessage.edit(progress)
            cleanup()
            return
        updateDonor(thedonor)
        return
    
initLastTransfersAndUpdateDonorDatabaseUpdatingTheStuffWithHeartToBeHappyWhenAllOfThisWorks()
client.run("token here")