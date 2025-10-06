#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Main function performing DA over a cell

Author: Esteban Alonso González - alonsoe@ipe.csic.es
"""
import os
import pdcast as pdc
import warnings
import numpy as np
import pandas as pd
import config as cfg
import modules.internal_fns as ifn
import modules.filters as flt
from modules.internal_class import SnowEnsemble

if cfg.numerical_model == 'FSM2':
    import modules.fsm_tools as model
elif cfg.numerical_model == 'dIm':
    import modules.dIm_tools as model
elif cfg.numerical_model == 'snow17':
    import modules.snow17_tools as model
else:
    raise Exception('Model not implemented')


def cell_assimilation(lat_idx, lon_idx):

    save_ensemble = cfg.save_ensemble
    real_time_restart = cfg.real_time_restart

    if save_ensemble:
        name_ensemble = "ensbl_" + str(lat_idx) +\
            "_" + str(lon_idx) + ".pkl.blp"
        name_ensemble = os.path.join(cfg.save_ensemble_path, name_ensemble)

    if real_time_restart:
        name_restart = "init_" + str(lat_idx) +\
            "_" + str(lon_idx) + ".pkl.blp"
        name_restart = os.path.join(cfg.real_time_restart_path, name_restart)

    if cfg.load_prev_run:
        filename = ("Reconstructed_cell_" + str(lat_idx)
                    + "_" + str(lon_idx) + ".pkl.blp")
    else:
        filename = ("cell_" + str(lat_idx) + "_" + str(lon_idx) + ".pkl.blp")

    filename = os.path.join(cfg.output_path, filename)

    # Check if file allready exist if is a restart run
    if (cfg.restart_run and os.path.exists(filename)):
        return None

    dates_obs = ifn.get_dates_obs()
    observations, errors = ifn.obs_array(dates_obs, lat_idx, lon_idx)

    if isinstance(observations, str):  # check if masked
        return None

    main_forcing = model.forcing_table(lat_idx, lon_idx)

    if ifn.forcing_check(main_forcing):
        print("NA's found in: " + str(lat_idx) + "," + str(lon_idx))
        return None

    time_dict = ifn.simulation_steps(observations, dates_obs)

    # If no obs in the cell or det_OL, run openloop, unless cfg.load_prev_run
    if (np.isnan(observations).all() or
            cfg.da_algorithm == "deterministic_OL") and not cfg.load_prev_run:
        ifn.run_model_openloop(lat_idx, lon_idx, main_forcing, filename)
        return None

    # Inicialice results dataframes
    # TODO: make function
    DA_Results = model.init_result(time_dict["del_t"], DA=True)  # DA parameter
    updated_Sim = model.init_result(time_dict["del_t"])  # posterior simulaiton
    sd_Sim = model.init_result(time_dict["del_t"])       # posterios stndr desv
    OL_Sim = model.init_result(time_dict["del_t"])       # OL simulation
    prior_mean = model.init_result(
        time_dict["del_t"])       # prior_mean simulation
    prior_sd = model.init_result(
        time_dict["del_t"])       # prior_sd simulation

    if cfg.da_algorithm in ['IES-MCMC', 'IES-MCMC_AI']:
        mcmc_Sim = model.init_result(time_dict["del_t"])
        mcmcSD_Sim = model.init_result(time_dict["del_t"])

    # initialice Ensemble class
    # open previous ensemble if reastart (not if reconstruct)
    if real_time_restart and not cfg.load_prev_run:
        try:
            Ensemble = ifn.io_read(name_restart)
            Ensemble.real_time_restart = True
        except FileNotFoundError:
            Ensemble = SnowEnsemble(lat_idx, lon_idx)
    else:
        Ensemble = SnowEnsemble(lat_idx, lon_idx)

    # Loop over assimilation steps
    for step in range(len(time_dict["Assimilaiton_steps"])-1):

        # subset forcing, errors and observations
        observations_sbst = observations[time_dict["Assimilaiton_steps"][step]:
                                         time_dict["Assimilaiton_steps"][step
                                                                         + 1]]
        error_sbst = errors[time_dict["Assimilaiton_steps"][step]:
                            time_dict["Assimilaiton_steps"][step
                                                            + 1]]

        forcing_sbst = main_forcing[time_dict["Assimilaiton_steps"][step]:
                                    time_dict["Assimilaiton_steps"][step + 1]]\
            .copy()

        Ensemble.create(forcing_sbst, observations_sbst, error_sbst, step)

        # store prior ensemble
        model.store_sim(prior_mean, prior_sd, Ensemble,
                        time_dict, step, save_prior=True)

        if cfg.load_prev_run:
            # HACK: Simply, store the prior before any DA to reconstruct
            # and exit

            # Write results
            cell_data = {"Ensemble_mean": prior_mean,
                         "Ensemble_sd": prior_sd}
            ifn.io_write(filename, ifn.downcast_output(cell_data))
            return None

        step_results = flt.implement_assimilation(Ensemble, step)

        # Store results in dataframesprior_mean
        model.storeDA(DA_Results, step_results, observations_sbst, error_sbst,
                      time_dict, step)
        model.store_sim(updated_Sim, sd_Sim, Ensemble,
                        time_dict, step)

        if cfg.da_algorithm in ['IES-MCMC', 'IES-MCMC_AI']:
            model.store_sim(mcmc_Sim, mcmcSD_Sim, Ensemble,
                            time_dict, step, MCMC=True)

        # If redraw, calculate the postrior shape
        if cfg.redraw_prior:
            Ensemble.posterior_shape()

        # Resample if filtering
        if cfg.da_algorithm in ["PF", "PBS"]:
            Ensemble.resample(step_results["resampled_particles"])
        # Optionally, creating new parameters per season (after resampling)
        if cfg.da_algorithm in ["PBS", "ProPBS", "AdaPBS", "ES",
                                "IES", "PIES", "IES-MCMC"]:
            Ensemble.season_rejuvenation()

    # Store OL
    model.storeOL(OL_Sim, Ensemble, observations_sbst,
                  time_dict, step)

    # Save some space
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')

        DA_Results = pdc.downcast(DA_Results,
                                  numpy_dtypes_only=True)
        OL_Sim = pdc.downcast(OL_Sim,
                              numpy_dtypes_only=True)
        updated_Sim = pdc.downcast(updated_Sim,
                                   numpy_dtypes_only=True)
        sd_Sim = pdc.downcast(sd_Sim,
                              numpy_dtypes_only=True)
        prior_mean = pdc.downcast(prior_mean,
                                  numpy_dtypes_only=True)
        prior_sd = pdc.downcast(prior_sd,
                                numpy_dtypes_only=True)
    # Write results
    cell_data = {"DA_Results": DA_Results,
                 "OL_Sim": OL_Sim,
                 "updated_Sim": updated_Sim,
                 "sd_Sim": sd_Sim,
                 "prior_mean": prior_mean,
                 "prior_sd": prior_sd}

    if cfg.da_algorithm in ['IES-MCMC', 'IES-MCMC_AI']:
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')

            mcmc_Sim = pdc.downcast(mcmc_Sim,
                                    numpy_dtypes_only=True)
            mcmcSD_Sim = pdc.downcast(mcmcSD_Sim,
                                      numpy_dtypes_only=True)

        cell_data['mcmc_Sim'] = mcmc_Sim
        cell_data['mcmcSD_Sim'] = mcmcSD_Sim

    # downcast and write output
    ifn.io_write(filename, ifn.downcast_output(cell_data))

    # Save ensemble
    if (save_ensemble):
        ifn.io_write(name_ensemble, Ensemble)

    if real_time_restart:  # save space
        Ensemble.forcing = []  # save some space
        Ensemble.origin_state = pd.DataFrame()
        Ensemble.state_membres = [0 for i in range(Ensemble.members)]
        ifn.io_write(name_restart, Ensemble)
