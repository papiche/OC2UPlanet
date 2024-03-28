# OC2UPlanet
Code to maintain equilibrium between an OpenCollective account and a UPlanet

```~/.zen/Astroport.ONE``` module



1. Create .env

```
#######################################################################
## Open Collective API KEY
## https://docs.opencollective.com/help/contributing/development/api
#######################################################################
OCAPIKEY="xxxxxxxxxxxxxxxxxxxx"
OCSLUG="yyyyyyyyyy"

#######################################################################
## UPLANET SECRETS
#######################################################################
UPLANETNAME="" ## ~/.ipfs/swarm.key for PRIVATE UPLANET

#######################################################################
### PLAYER ZERO NACL CREDENTIALS ## NEEDED FOR EMPTY UPLANETNAME
#######################################################################
SALT="secret phrase one"
PEPPER="secret phrase two"
```

2. Run daemon.sh


```
./oc2uplanet.sh &
```

3. Check logs

```
tail -f ~/.zen/tmp/oc2uplanet.log
```
