# app/config.py
#
# Samlar konstanter och konfigurationsvärden som används
# på flera ställen i applikationen.
#
# Här ska värden som påverkar applikationens beteende ligga,
# men inte själva Flask-konfigurationen.
#
# Exempel:
# - säkerhetsgränser
# - tidsgränser
# - standardvärden
#
# Miljöberoende värden (databasadress, hemliga nycklar osv)
# bör istället läsas från miljövariabler i __init__.py.
#

MAX_TOKENS_PER_STUDENT = 5