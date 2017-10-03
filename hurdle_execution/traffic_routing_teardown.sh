#!/usr/bin/env bash

####################################################################################################
# This script will tear down the traffic generator static routes to get back to a clean
# routing table state
####################################################################################################

TGEN1_SUBNET=192.168.101.0/24
TGEN2_SUBNET=192.168.102.0/24
TGEN3_SUBNET=192.168.103.0/24
TGEN4_SUBNET=192.168.104.0/24
TGEN5_SUBNET=192.168.105.0/24
TGEN6_SUBNET=192.168.106.0/24

TGEN1_GW=192.168.101.1
TGEN2_GW=192.168.102.1
TGEN3_GW=192.168.103.1
TGEN4_GW=192.168.104.1
TGEN5_GW=192.168.105.1
TGEN6_GW=192.168.106.1

TGEN_SUBNETS=(${TGEN1_SUBNET}
              ${TGEN2_SUBNET}
              ${TGEN3_SUBNET}
              ${TGEN4_SUBNET}
              ${TGEN5_SUBNET}
              ${TGEN6_SUBNET}
              )

TGEN_GWS=(${TGEN1_GW}
          ${TGEN2_GW}
          ${TGEN3_GW}
          ${TGEN4_GW}
          ${TGEN5_GW}
          ${TGEN6_GW}
          )


echo "The current routing table is:"
route

echo ""
echo "Now removing static routes for each of 6 traffic generators"

for i in "${!TGEN_SUBNETS[@]}"; do 
  printf "Removing route %s of 6 for subnet %s to gateway %s\n" "$(($i+1))" "${TGEN_SUBNETS[$i]}" "${TGEN_GWS[$i]}"
  route del -net ${TGEN_SUBNETS[$i]} gw ${TGEN_GWS[$i]}
  rc=$?
  if [[ $rc != 0 ]]
    then
      printf "Removal of route %s of 6 failed, exiting. Please email the Phase 2 Hurdle email alias for help\n" "$(($i+1))"
      exit $rc
    else
      printf "Removal of route %s of 6 succeeded\n" "$(($i+1))"
  fi
done

echo "Traffic generation static routes are now removed. New Routing table:"
route

 
