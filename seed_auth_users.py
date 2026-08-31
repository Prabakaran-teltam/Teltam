import os
import sys
import io
import csv
from datetime import datetime

# Setup Django environment
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')

import django
django.setup()

from django.contrib.auth.models import User
from django.utils.dateparse import parse_datetime
from django.utils import timezone

RAW_USER_CSV = """"id","password","last_login","is_superuser","username","first_name","last_name","email","is_staff","is_active","date_joined"
1,"pbkdf2_sha256$600000$VRjn0XnVBVoXVMwG6F3KfQ$nr39msDpx+nun7mI6O52z8EOITuxBc6jHlX4Mep+kMg=","2026-07-29 11:32:20.743823+05:30",True,"admin","","","admin@gmail.com",True,True,"2025-07-04 17:00:30.00538+05:30"
2,"pbkdf2_sha256$600000$39rs2fhDRz7ZZ2JaQSMhno$kuvRvF7q1lpvTrBR3ADD0z9CbjMQMzidOZqUwvxgFUo=","2026-04-20 19:14:56.958895+05:30",False,"Gowtham","","","1croreprojectsteam@gmail.com",False,True,"2025-07-05 09:40:00.593622+05:30"
3,"pbkdf2_sha256$600000$68Noq3IbWZWmGh958nF4yR$F8EHH2v5dnIlYbdlegriKFFbxHbbSNRerD1NwjSfXTI=",NULL,False,"Prabakaran","","","somethingtalk1@gmail.com",False,False,"2025-07-05 11:05:59.765227+05:30"
4,"pbkdf2_sha256$600000$eprTbP7VmyEOuiDOa3b8jm$rmu6eWpBPtLY46zXuR9knm010C2v+T6MNyJSGsnbiG4=","2025-07-12 11:35:31.141852+05:30",False,"prabakaran_thl","","","prabakaran_thl@yahoo.co.in",False,True,"2025-07-05 11:10:36.485336+05:30"
5,"pbkdf2_sha256$600000$OUxeBs2yisHyuEGeyXrjMZ$nNcHxXuXS4tb5b/o3VeyE0sf/B5PQwOLVPEbr+AxmU4=","2025-07-05 12:27:53.880362+05:30",False,"Thilagarani","","","rakvtv@gmail.com",False,True,"2025-07-05 12:27:18.983374+05:30"
6,"pbkdf2_sha256$600000$oV3EwaPITBJR4gdzeM3fBN$khGgRySpYQjCGkwN9ztNSpiGnyxrq2bR0H8e5nxXWeg=","2025-09-06 21:00:34.334694+05:30",True,"Ajithkumar","","","ajitheee22@gmail.com",True,True,"2025-07-05 19:04:40.986351+05:30"
7,"pbkdf2_sha256$600000$0bitzYy5dQd1KNPQo210j9$t5n2eFu3nRcIRw8TG/SKSG2ahEn2Dm4Tv6dc2rN4WUg=","2025-07-05 22:25:35.741513+05:30",True,"Ashok","","","ashok.karuppuchamy@gmail.com",True,True,"2025-07-05 22:24:20.873307+05:30"
8,"pbkdf2_sha256$600000$01oVYemkRj4JwFYKAE1xjy$qiAMI08aGwUUIVqoj2SNxQ1TqbUI2SiG5MPOxEDAydg=","2025-07-13 19:46:40.651329+05:30",False,"Arun","","","arun.janakiraman87@gmail.com",False,True,"2025-07-13 19:45:13.874318+05:30"
9,"pbkdf2_sha256$600000$KkafN3R3wTN3nGDOm1P6B9$p+xk/YInfUA8gCr+deMqG7jA876IdHTnlHF1kjmttTU=","2025-07-24 22:20:54.652678+05:30",False,"rajupetap@gmail.com","","","rajupetap@gmail.com",False,True,"2025-07-24 22:19:46.128947+05:30"
10,"pbkdf2_sha256$600000$WddHKiG9FO9uZ2yw90nsCZ$s1PM+VefUl0x+G1sVovw21xA/A4EhKFz5REppV0H1tw=","2025-07-26 19:04:32.406292+05:30",False,"thirumoorthy","","","stm.moorthy@gmail.com",False,True,"2025-07-26 19:03:51.336899+05:30"
11,"pbkdf2_sha256$600000$qS10u9Fst5JxtsDyC4Z7sH$OXFslFxN5J3Vp7lt5ZWcu1wEFCq0U6nlUQeTWbMYjQE=","2025-08-01 00:20:57.750114+05:30",False,"pmanu033","","","pmanu033@gmail.com",False,True,"2025-08-01 00:20:32.959387+05:30"
12,"pbkdf2_sha256$600000$9GBAehqQXy495LU6mB5EwL$pLW0rU8FmPoMFzL53mbNU/3phHzOyzgwipcT9c1zVDs=",NULL,False,"SATHISH","","","miraclewalajaa@gmail.com",False,False,"2025-08-07 11:34:50.222647+05:30"
13,"pbkdf2_sha256$600000$gxMjLjd9Hs9JcyEkOIoBie$rRF2PlhubWBOu7B8+M72NoKT9NqKa3V3U6RFJjuLXCg=",NULL,False,"miraclenetcafe","","","miraclewalajaa@gmail.com",False,False,"2025-08-07 11:37:37.992593+05:30"
14,"pbkdf2_sha256$600000$daIs7iYZ4Of6dNRZn0uKr2$yVV6Ane9A2X0B2pABmC9s9zE00OWNTBY/7OYFL2P/+0=","2025-09-08 13:40:54.528+05:30",False,"Murali","","","muralidharanark@gmail.com",False,True,"2025-09-08 13:40:03.968358+05:30"
15,"pbkdf2_sha256$600000$o4I5QX0cgWspKYbWRo9031$HF+6LJCvV+KNR8SceAQajanutBRBJzTgsmLn/8/G1bo=","2025-10-11 19:56:59.072099+05:30",True,"Eshwar","","","ekambareswaran.j@gmail.com",True,True,"2025-09-10 13:58:12.529187+05:30"
16,"pbkdf2_sha256$600000$1VJw7EiDHI5tiraCnjWgIV$fvWjmUYCnYWfVrWKd2TJfwSO0x9767ths5dTfKSJKPg=","2025-09-16 12:03:04.34832+05:30",False,"Manikandan","","","mani.chinnaraju@gmail.com",False,True,"2025-09-16 12:01:49.823149+05:30"
17,"pbkdf2_sha256$600000$e1vcncnSQZTE3356QS2A52$f5qRzFNYW7Zx1UjFon0rSWqqBH7v8zcXcxDTsNcNSsU=",NULL,False,"Nivetha","","","gowtham.13ni@gmail.com",False,False,"2025-10-24 16:44:41.241046+05:30"
18,"pbkdf2_sha256$600000$mSrt8HzyYzAHUOHzenpHoL$Vw+XoItTix7Vqbg1/36K2PUrX28b6nKW/PFZKLVuFvc=",NULL,False,"Bala","","","ragubala2001@gmail.com",False,False,"2025-10-24 16:48:17.079624+05:30"
19,"pbkdf2_sha256$600000$cNtoLZLQVahpzcERdkY6uQ$N/x0qIIU419jryvR4KFCyQcEUxKB0Ol8x8vdGOQM0cE=","2025-11-06 14:01:16.24887+05:30",False,"sachin.swami","","","sachin.swami.ai@gmail.com",False,True,"2025-11-06 13:59:57.070214+05:30"
20,"pbkdf2_sha256$600000$CHoUQKDPUBp9dvpYgXcmrG$xCHpQNabDgQq7DMEM68FOfQpc2lLQSn2B1NNEGm5gUQ=",NULL,False,"ram","","","ram@gmail.com",False,False,"2025-11-06 15:05:24.011981+05:30"
21,"pbkdf2_sha256$600000$JH0QkDwyvOwHkwS02B2Htc$p5DuK/5MhH/f+ndGtA6DoG1B4moNvY26FCTvHDPFrwM=",NULL,False,"Gunguun","","","julaykaht@gmail.com",False,False,"2025-11-17 09:39:24.524079+05:30"
22,"pbkdf2_sha256$600000$9xCor4YidQGZcbFv4GWf7c$8aqkRap20mRCvft9qVpegDShIm7h8tHEPrEDkoJImA0=",NULL,False,"_Tayammum_","","","julaykaht@gmail.com",False,False,"2025-11-17 09:40:33.890357+05:30"
23,"pbkdf2_sha256$600000$GwcmMynOI1B6jnH4vZAmB2$uydvcU3/N0gRY5skO0ImEmEmIZcVNfB/6n2udi2+WCo=",NULL,False,"Tayammum_fatehiii_","","","julaykaht@gmail.com",False,False,"2025-11-17 09:42:53.244266+05:30"
24,"pbkdf2_sha256$600000$LjMbI1wrxFzB9t3s9Aozc2$aocxFCvn/qVflcmAz1g8pvRkGjPaEu520rDaWWFgc+A=",NULL,False,"Taya_mmum","","","julaykaht@gmail.com",False,False,"2025-11-17 19:04:53.65925+05:30"
25,"pbkdf2_sha256$600000$S9Iul8StiTPszjRCqytP7q$zcs7PL+0Oa1fdcb36twn4CqItcyzOoibaL8Vl6P8uiI=","2025-11-24 12:43:43.869405+05:30",False,"devil","","","d05924233@gmail.com",False,True,"2025-11-24 12:43:07.075044+05:30"
26,"pbkdf2_sha256$600000$WuXTUIjzxWJL7sqK01bGdT$Dd77a2KRTCTQh7lkDNFXClAAcY3SeQOxq7DG09Hjsq0=","2025-12-26 16:17:36.45119+05:30",False,"vijay.kumarsvpr","","","vijay.kumarsvpr@gmail.com",False,True,"2025-12-26 16:16:55.315864+05:30"
27,"pbkdf2_sha256$600000$5r0gKYM0kxsjABKJwftEjP$C+bFuE63lHsZEUj9Da4YGP0Z1HZjbf0IuV1J1etg6Z0=","2025-12-31 12:29:57.893745+05:30",False,"Jaya@AI","","","jaya.maheswari.lakshmi@gmail.com",False,True,"2025-12-31 12:28:21.621393+05:30"
28,"pbkdf2_sha256$600000$66Fgddvu1AhRIh6XOUX9dI$Tiw3m0rzityh/jKe0HJrKFqJPoWIjjP4g5WjVdj2w0s=","2026-01-13 01:18:52.642148+05:30",False,"Preeti","","","TURSHANIPREETI@gmail.com",False,True,"2026-01-13 01:18:09.699386+05:30"
29,"pbkdf2_sha256$600000$08SzLytXIvOspBwM8XNZks$wzH8wq6twO9drSSOIzrIy/6QpMuG30yj6/dURFEOI+Q=","2026-02-24 14:45:49.069668+05:30",False,"Pavithra","","","pavithra.dlktechnologies@gmail.com",False,True,"2026-02-24 14:45:01.434131+05:30"
30,"pbkdf2_sha256$600000$AC4GWn6u072xlLf21bDPQt$ziMSrf8b9DPSNf2D5MOQ5F1tF0a6L5ob1ooC8rMANDc=","2026-03-14 01:36:32.045831+05:30",False,"Raghu298","","","mahakudraghunath298@gmail.com",False,True,"2026-03-14 01:36:05.471425+05:30"
31,"pbkdf2_sha256$600000$HZPbbPaM0nkuADLIg8H9Gp$8CJFSEtjox0uP1vaMwOcP8LGIcKus5rWdNDS7/3oxUk=","2026-03-23 08:14:42.176157+05:30",False,"maalusundu","","","amadangarli@bellsouth.net",False,True,"2026-03-23 08:13:50.312544+05:30"
32,"pbkdf2_sha256$600000$isFcIbXCaOTSg3SCIPhxS7$YZ/AqeldWoqGRLRRjwory9Cvh63CyTZBCwPRPbACFAA=","2026-03-25 22:36:53.031764+05:30",False,"Selvapremkumar","","","Selvapremkumar.k@gmail.com",False,True,"2026-03-25 22:24:18.660512+05:30"
33,"pbkdf2_sha256$600000$ag0PbgKARO7hOktFMk34qO$PY6geFA811Ytaw7gqoFDPUU4tpvSgvu4fasYvi/AggM=","2026-04-06 18:13:32.018444+05:30",False,"meenatchi","","","meenatchidlksolution@gmail.com",False,True,"2026-04-06 18:12:16.735218+05:30"
34,"pbkdf2_sha256$600000$FROmtuSX9h7ucIyXWDnshP$hMfrMTFIcN5xqfQWkwbQNe28cZXOgykZSBnUh5HNnbo=","2026-04-21 16:32:03.406032+05:30",False,"Prabakara","","","prabakaranbigdata@gmail.com",False,True,"2026-04-21 16:31:29.79623+05:30"
35,"pbkdf2_sha256$600000$IEHV2nsRK0IDVjpZxt6uvi$xAvluuvfDalEcYz0F0klWE46s0lLFKwl7QfPgnyQFUw=","2026-04-27 20:51:47.155627+05:30",False,"a.balavinayakar","","","a.balavinayakarusa@gmail.com",False,True,"2026-04-27 20:49:57.2173+05:30"
36,"pbkdf2_sha256$600000$S3sTYB1aelm3gasMSCX4ed$GJkphb4YDogBspKlTdAfsVPaj/BXKY4yu/7QO+yLANc=","2026-04-27 21:23:58.392173+05:30",False,"vrsusesai","","","venkat271176@gmail.com",False,True,"2026-04-27 21:23:19.065475+05:30"
37,"pbkdf2_sha256$600000$Rmz6palaOMq7Q3fah3oKDn$zU3Rk8l7eT8PF6imgDso3HNpB6Upvb2er74BcG9Dlos=","2026-06-05 13:12:59.26057+05:30",False,"Rosoo","","","roosod@gmail.com",False,True,"2026-06-05 13:12:14.635815+05:30"
38,"pbkdf2_sha256$600000$IbjaAZJGjSfrLAHpnFCEjQ$UN7flL+906XNBANDU8wtThGSOxhcDR1b+Tb3XEFI3DM=","2026-06-19 00:14:08.781389+05:30",False,"senthil99","","","senthilranganath@gmail.com",False,True,"2026-06-18 08:25:50.471319+05:30"
39,"pbkdf2_sha256$600000$z1BjGvSqYia9pernqPujj1$SrZq1drrK1f1iScuFWPA8Oo4Nmf6gfNoE9/Qu5GiTeU=","2026-07-10 19:05:18.722114+05:30",False,"Varshini","","","mahadhasyamvarshini@gmail.com",False,True,"2026-07-10 19:04:43.159648+05:30"
40,"pbkdf2_sha256$600000$7vnTQR7zAIlRbIBQn2SIGQ$z/1eX1b53opyli/cSAc/IQHfPgGEyWphAc34T45kVB4=","2026-08-03 11:40:03.557362+05:30",False,"girirajanrl","","","girirajan.r1234@gmail.com",False,True,"2026-08-03 11:38:55.831236+05:30"
"""

def parse_bool(val):
    if isinstance(val, bool):
        return val
    s = str(val).strip().lower()
    return s in ('true', '1', 't', 'yes')

def parse_dt(val):
    if not val or str(val).strip().upper() in ('NULL', 'NONE', ''):
        return None
    try:
        dt = parse_datetime(str(val).strip())
        if dt and timezone.is_naive(dt):
            dt = timezone.make_aware(dt)
        return dt
    except Exception:
        return None

def seed_users():
    f = io.StringIO(RAW_USER_CSV.strip())
    reader = csv.DictReader(f)
    
    created_count = 0
    updated_count = 0
    
    print("Starting Django auth_user data import...")
    
    for row in reader:
        user_id = int(row['id'])
        password = row['password']
        last_login = parse_dt(row['last_login'])
        is_superuser = parse_bool(row['is_superuser'])
        username = row['username'].strip()
        first_name = row['first_name'].strip()
        last_name = row['last_name'].strip()
        email = row['email'].strip()
        is_staff = parse_bool(row['is_staff'])
        is_active = parse_bool(row['is_active'])
        date_joined = parse_dt(row['date_joined']) or timezone.now()

        # Check if user with ID or Username exists
        user = User.objects.filter(id=user_id).first()
        if not user:
            user = User.objects.filter(username=username).first()

        is_new = False
        if not user:
            user = User(id=user_id, username=username)
            is_new = True

        user.password = password  # Retain exact pre-hashed password string
        user.username = username
        user.first_name = first_name
        user.last_name = last_name
        user.email = email
        user.is_superuser = is_superuser
        user.is_staff = is_staff
        user.is_active = is_active
        user.last_login = last_login
        user.date_joined = date_joined
        
        user.save()

        if is_new:
            created_count += 1
            print(f"[CREATED] ID: {user.id} | Username: {user.username} | Email: {user.email}")
        else:
            updated_count += 1
            print(f"[UPDATED] ID: {user.id} | Username: {user.username} | Email: {user.email}")

    print(f"\nImport Completed Successfully! Total Created: {created_count}, Total Updated: {updated_count}")

    # Reset PostgreSQL primary key sequence generator to prevent IntegrityError on new registrations
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute("SELECT setval(pg_get_serial_sequence('auth_user', 'id'), COALESCE(MAX(id), 1)) FROM auth_user;")
        max_id = cursor.fetchone()[0]
        print(f"[SEQUENCE RESET] auth_user_id_seq updated to {max_id}")

if __name__ == '__main__':
    seed_users()
