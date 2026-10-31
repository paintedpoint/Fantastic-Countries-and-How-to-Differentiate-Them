import pandas as pd

airports = pd.read_csv("airports.csv", low_memory=False, 
                       keep_default_na=False, na_values=[""])
routes   = pd.read_csv("routes.csv",
                       keep_default_na=False, na_values=[""])
airlines = pd.read_csv("airlines.csv")

# skipping metadata
pop  = pd.read_csv("countryPop.csv", skiprows=4)
area = pd.read_csv("countryLandArea.csv", skiprows=4)

# Nambia is listed as NA in the csv and we have a difference in iso codes being used. To combine them, I'll fix the iso codes and the join based off that

YEAR = "2023"

# --- Lookup table: ISO 3-letter code -> 2-letter code (pairs, written as text) ---
CODES = """
AFG AF  ALA AX  ALB AL  DZA DZ  ASM AS  AND AD  AGO AO  AIA AI  ATA AQ  ATG AG  ARG AR
ARM AM  ABW AW  AUS AU  AUT AT  AZE AZ  BHS BS  BHR BH  BGD BD  BRB BB  BLR BY  BEL BE
BLZ BZ  BEN BJ  BMU BM  BTN BT  BOL BO  BES BQ  BIH BA  BWA BW  BVT BV  BRA BR  IOT IO
BRN BN  BGR BG  BFA BF  BDI BI  CPV CV  KHM KH  CMR CM  CAN CA  CYM KY  CAF CF  TCD TD
CHL CL  CHN CN  CXR CX  CCK CC  COL CO  COM KM  COG CG  COD CD  COK CK  CRI CR  CIV CI
HRV HR  CUB CU  CUW CW  CYP CY  CZE CZ  DNK DK  DJI DJ  DMA DM  DOM DO  ECU EC  EGY EG
SLV SV  GNQ GQ  ERI ER  EST EE  SWZ SZ  ETH ET  FLK FK  FRO FO  FJI FJ  FIN FI  FRA FR
GUF GF  PYF PF  ATF TF  GAB GA  GMB GM  GEO GE  DEU DE  GHA GH  GIB GI  GRC GR  GRL GL
GRD GD  GLP GP  GUM GU  GTM GT  GGY GG  GIN GN  GNB GW  GUY GY  HTI HT  HMD HM  VAT VA
HND HN  HKG HK  HUN HU  ISL IS  IND IN  IDN ID  IRN IR  IRQ IQ  IRL IE  IMN IM  ISR IL
ITA IT  JAM JM  JPN JP  JEY JE  JOR JO  KAZ KZ  KEN KE  KIR KI  PRK KP  KOR KR  KWT KW
KGZ KG  LAO LA  LVA LV  LBN LB  LSO LS  LBR LR  LBY LY  LIE LI  LTU LT  LUX LU  MAC MO
MDG MG  MWI MW  MYS MY  MDV MV  MLI ML  MLT MT  MHL MH  MTQ MQ  MRT MR  MUS MU  MYT YT
MEX MX  FSM FM  MDA MD  MCO MC  MNG MN  MNE ME  MSR MS  MAR MA  MOZ MZ  MMR MM  NAM NA
NRU NR  NPL NP  NLD NL  NCL NC  NZL NZ  NIC NI  NER NE  NGA NG  NIU NU  NFK NF  MKD MK
MNP MP  NOR NO  OMN OM  PAK PK  PLW PW  PSE PS  PAN PA  PNG PG  PRY PY  PER PE  PHL PH
PCN PN  POL PL  PRT PT  PRI PR  QAT QA  REU RE  ROU RO  RUS RU  RWA RW  BLM BL  SHN SH
KNA KN  LCA LC  MAF MF  SPM PM  VCT VC  WSM WS  SMR SM  STP ST  SAU SA  SEN SN  SRB RS
SYC SC  SLE SL  SGP SG  SXM SX  SVK SK  SVN SI  SLB SB  SOM SO  ZAF ZA  SGS GS  SSD SS
ESP ES  LKA LK  SDN SD  SUR SR  SJM SJ  SWE SE  CHE CH  SYR SY  TWN TW  TJK TJ  TZA TZ
THA TH  TLS TL  TGO TG  TKL TK  TON TO  TTO TT  TUN TN  TUR TR  TKM TM  TCA TC  TUV TV
UGA UG  UKR UA  ARE AE  GBR GB  USA US  UMI UM  URY UY  UZB UZ  VUT VU  VEN VE  VNM VN
VGB VG  VIR VI  WLF WF  ESH EH  YEM YE  ZMB ZM  ZWE ZW  XKX XK
"""

# Loop 1: turn the text into a dictionary (every 2 words = one pair)
tokens = CODES.split()
a3_to_a2 = {}
for i in range(0, len(tokens), 2):
    a3_to_a2[tokens[i]] = tokens[i + 1]

# Loop 2: land area lookup by 3-letter code
area_by_code = {}
for i in range(len(area)):
    area_by_code[area.loc[i, "Country Code"]] = area.loc[i, YEAR]

# Loop 3: build the clean country table, one row at a time
rows = []
dropped = []
for i in range(len(pop)):
    name = pop.loc[i, "Country Name"]
    a3 = pop.loc[i, "Country Code"]
    population = pop.loc[i, YEAR]
    land = area_by_code.get(a3)

    if a3 not in a3_to_a2:                      # not a real country -> aggregate
        dropped.append(name)
        continue
    if pd.isna(population) or land is None or pd.isna(land):
        dropped.append(name + " (missing data)")
        continue

    rows.append({"country": name, "iso_country": a3_to_a2[a3],
                 "population": population, "land_km2": land})

countries = pd.DataFrame(rows)
print(len(dropped), "dropped:", dropped)
print(countries.shape)

# Which types count as a real, open airfield
EXCLUDE = ["closed", "heliport", "balloonport"]

# Two tallies: country code -> number of airports
open_count = {}
scheduled_count = {}

# zip() walks three columns together, row by row:
# each pass gives us one airport's country, type, and scheduled flag
for code, kind, sched in zip(airports["iso_country"],
                             airports["type"],
                             airports["scheduled_service"]):
    if kind in EXCLUDE:
        continue                      # skip closed / heliports / balloonports
    if code not in open_count:        # first time we see this country
        open_count[code] = 0
        scheduled_count[code] = 0
    open_count[code] += 1             # every surviving airfield counts here
    if sched == "yes":
        scheduled_count[code] += 1    # only scheduled ones count here

# Attach the tallies to the country table (0 if a country has none)
countries["open_airfields"] = [open_count.get(c, 0) for c in countries["iso_country"]]
countries["scheduled_airports"] = [scheduled_count.get(c, 0) for c in countries["iso_country"]]

# Sanity checks
print(countries["open_airfields"].sum(), countries["scheduled_airports"].sum())
print(countries.sort_values("open_airfields", ascending=False).head(10)[
      ["country", "open_airfields", "scheduled_airports"]])
print("Countries with zero scheduled airports:",
      (countries["scheduled_airports"] == 0).sum())

# Airports per 1,000 km² of land (geographic coverage)
countries["open_per_1000km2"]  = countries["open_airfields"]      / countries["land_km2"] * 1000
countries["sched_per_1000km2"] = countries["scheduled_airports"]  / countries["land_km2"] * 1000

# Airports per million people (supply vs. population)
countries["open_per_million"]  = countries["open_airfields"]      / countries["population"] * 1_000_000
countries["sched_per_million"] = countries["scheduled_airports"]  / countries["population"] * 1_000_000

# What share of a country's airfields have airline service?
countries["share_scheduled"] = countries["scheduled_airports"] / countries["open_airfields"]

def show_top(col, df, n=10):
    print("\n", col)
    print(df.sort_values(col, ascending=False).head(n)[
          ["country", col, "open_airfields", "scheduled_airports", "population"]].to_string())

for col in ["open_per_1000km2", "sched_per_1000km2", "open_per_million", "sched_per_million"]:
    show_top(col, countries)

# countries with at least 1 million people
big = countries[countries["population"] >= 1_000_000]
for col in ["open_per_1000km2", "sched_per_1000km2", "open_per_million", "sched_per_million"]:
    show_top(col, big)
