import time
import os

import numpy as np
import h5py as h5

import torch
import torch.nn as nn
import torch.nn.functional as F

from classynet.models.model import Model
from classynet.models import common

class Net_ST1(Model):

    HYPERPARAMETERS_DEFAULTS = {
            "learning_rate": 1e-3,
            }

    def __init__(self, k, hp=None):
        super().__init__(k)

        n_inputs_cosmo = len(common.INPUTS_COSMO)
        n_inputs_tau = 2
        n_k = len(k)

        self.lin_cosmo = nn.Linear(n_inputs_cosmo, 20)
        self.lin_tau = nn.Linear(1, 133)

        self.lin_combined = nn.Sequential(
            nn.PReLU(),
            nn.Linear(self.lin_cosmo.out_features + self.lin_tau.out_features, 500),
            nn.PReLU(),
            nn.Linear(500, n_k)
        )

        self.learning_rate = 1e-3

        self.output_normalization = nn.Parameter(torch.ones(1), requires_grad=False)


    def forward(self, x):
        self.k_min = x["k_min"][0]
        inputs_cosmo = common.get_inputs_cosmo(x)
        inputs_tau = x["tau"][:, None]

        prediction = x["e_kappa"][:, None] * self.k[None, :] * self.lin_combined(
            torch.cat((
                self.lin_cosmo(inputs_cosmo),
                self.lin_tau(inputs_tau)
            ), dim=1)
        )

        return prediction

    def forward_reduced_mode(self, x,k_min_idx):
        self.k_min = x["k_min"][0]
        inputs_cosmo = common.get_inputs_cosmo(x)
        inputs_tau = x["tau"][:, None]

        prediction = x["e_kappa"][:, None] * self.k[None, :] * self.lin_combined(
            torch.cat((
                self.lin_cosmo(inputs_cosmo),
                self.lin_tau(inputs_tau)
            ), dim=1)
        )

        return torch.flatten(prediction[:,k_min_idx:] * self.output_normalization ) #torch.tensor([0.00020377613060535774]))

    def epochs(self):
        return 40

    def criterion(self):
        def loss(prediction, truth):
            return common.mse_truncate(self.k, self.k_min)(prediction, truth)
        return loss

    def optimizer(self):

        return torch.optim.Adam(self.parameters(), lr=self.learning_rate)

    def required_inputs(self):
        return set(common.INPUTS_COSMO + ["k_min", "k", "r_s", "k_d", "tau", "e_kappa"])

    def tau_training(self):
        return None

    def source_functions(self):
        return ["t1"]

    def lr_scheduler(self, opt):
        return torch.optim.lr_scheduler.LambdaLR(opt, lambda epoch: np.exp(-epoch / 8))
