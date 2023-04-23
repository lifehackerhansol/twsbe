import datetime
import os
from asyncio import queue

from cleaninty.ctr.ninja import NinjaManager, NinjaException
from cleaninty.ctr.simpledevice import SimpleCtrDevice
from cleaninty.ctr.soap.manager import CtrSoapManager
from cleaninty.ctr.soap import helpers, ias
from cleaninty.nintendowifi.soapenvelopebase import SoapCodeError


class SOAPHandle():
    def __init__(self):
        self.initDatabase()

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

    def initDatabase(self):
        seekcount = 0
        donors = os.listdir('./donors/')
        print("Initializing donors...")
        db = open("db.txt", "w")
        for i in range(len(donors)):
            lastmoved = self.getDonorCooldown(f"donors/{donors[i]}")
            donorentry = f"{donors[i]} {lastmoved}\n"
            db.seek(seekcount)
            db.write(donorentry)
            seekcount = seekcount + len(donorentry)
        db.close()
        print("Done!")
        return

    async def getReadyDonor(self):
        db = open("db.txt", "r")
        content = db.read()
        donors = content.splitlines()
        for i in range(len(donors)):
            donorlastmoved = donors[i].split()[1]
            currenttime = datetime.datetime.now().strftime("%Y-%b-%d")
            if currenttime - datetime.timedelta(days=7) > donorlastmoved:
                return f"donors/{donors[i]}"

    async def updateDonor(self, donor):
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
                db.write(self.getDonorCooldown(f"donors/{donors[i]}"))
                db.close()
                return
            offset = offset + len(donors[i])+1

    def checkReg(self, console):
        device = SimpleCtrDevice(json_file=console)
        soap_device = CtrSoapManager(device, False)
        helpers.CtrSoapCheckRegister(soap_device)
        device.serialize_json(json_file=console)
        print(f"region: {soap_device.region} country: {soap_device.country}")
        return [soap_device.country, soap_device.region]

    def _run_unregister(self, device, soap_device):
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

    def EShopRegionChange(self, console, region, country):
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
            self._run_unregister(device, soap_device)

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

    def _move_account(self, source_console, target_console):
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

    def _del_eshop(self, console):
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
        self._run_unregister(device, soap_device)

        print("Saving updated session...")
        device.serialize_json(json_file=console)

        print("Complete!")

    def checkSerialblacklist(self, serial):
        with open("serialblacklist.txt", "r") as f:
            for x in f:
                if serial == x:
                    return True

    def validSerial(self, serial, checkdigit):
        if not checkdigit:
            if self.checkSerialblacklist(serial):
                return 2
            return 0
        else:
            if self.checkSerialblacklist(serial[(len(serial)-1):]):
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

    def getCountry(self, region):
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

    def cleanup(self):
        try:
            os.remove("essential.exefs")
        except Exception:
            pass
        try:
            os.remove("otp.bin")
        except Exception:
            pass

    def getDonorCooldown(self, console):
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

    def confirmCountryMatch(self, target, donor):
        donorlocale = self.CheckReg(donor)
        targetlocale = self.CheckReg(target)
        if targetlocale != donorlocale:
            self._del_eshop(donor)
            erchangeresult = self.EShopRegionChange(donor, targetlocale[1], targetlocale[0])
            
            if erchangeresult == 0:
                return 0
            else:
                print(f"EShopRegionChange on donor failed. Make sure you put a fixed donor inside. Faulty donor: {donor} Soap error if not 1: {erchangeresult}")
                return 1
