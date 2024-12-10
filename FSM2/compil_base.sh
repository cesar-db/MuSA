#!/bin/bash

FC=gfortran
cd src

cat > OPTS.h << EOF
/* Process options                                  : Possible values */
#define ALBEDO pyALBEDO   /* snow albedo                   : 1, 2            */
#define CANINT pyCANINT   /* canopy interception of snow   : 1, 2            */
#define CANMOD pyCANMOD   /* forest canopy layers          : 1, 2            */
#define CANRAD pyCANRAD   /* canopy radiative properties   : 1, 2            */
#define CANUNL pyCANUL    /* unloading of canopy           : 1, 2            */
#define CONDCT pyCONDCT   /* snow thermal conductivity     : 0, 1            */
#define DENSTY pyDENSTY  /* snow density                  : 0, 1, 2         */
#define EXCHNG pyEXCHNG   /* turbulent exchange            : 0, 1            */
#define HYDROL pyHYDROL   /* snow hydraulics               : 0, 1, 2         */
#define SGRAIN pySGRAIN   /* snow grain growth             : 1, 2            */
#define SNFRAC pySNFRAC   /* snow cover fraction           : 1, 2            */
/* Driving data options                             : Possible values */
#define DRIV1D 1   /* 1D driving data format        : 1, 2            */
#define SWPART 0   /* SW radiation partition        : 0, 1            */
#define ZOFFST 1   /* measurement height offset     : 0, 1            */
/* Output options                                   : Possible values */
#define PROFNC 0   /* netCDF output                 : 0, 1            */
EOF

$FC -cpp -o FSM2 -O3 FSM2_MODULES.F90 FSM2_PARAMS.F90 FSM2.F90         \
FSM2_DRIVE.F90 FSM2_OUTPUT.F90 FSM2_VEG.F90 FSM2_TIMESTEP.F90          \
CANOPY.F90 INTERCEPT.F90 LUDCMP.F90 PSIMH.F90 QSAT.F90 SNOW.F90        \
SOIL.F90 SOLARPOS.F90 SRFEBAL.F90 SWRAD.F90 THERMAL.F90 TRIDIAG.F90    \
TWOSTREAM.F90
mv FSM2 ../FSM2
rm *.mod
cd ..
