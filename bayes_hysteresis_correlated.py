import matplotlib.pyplot as plt
import pyro
import pyro.distributions as dist
import pyro.infer
import pyro.optim
import torch
from pyro.nn import PyroModule, PyroSample
from bayes_hysteresis import BayesianHysteresis
import utils


def calculate_cov(model, sigma):
    mesh_points = model.mesh_points
    x = mesh_points[:, 0]
    y = mesh_points[:, 1]
    # create matrix of distances between points in vector
    n = len(x)
    distances = torch.empty((n, n)).to(model.h_data)

    for ii in range(n):
        for jj in range(n):
            distances[ii][jj] = torch.sqrt((x[ii] - x[jj]) ** 2 + (y[ii] - y[jj]) ** 2)

    # calculate correlation matrix using squared exponential
    corr = torch.exp(-distances ** 2 / (2.0 * sigma ** 2)) \
           + torch.eye(model.vector_shape) * 1e-2

    return corr


def calculate_prior_mean(model):
    # use distance from x=y to get prior mean
    mesh_points = model.mesh_points
    x = mesh_points[:, 0]
    y = mesh_points[:, 1]

    d = torch.abs(x - y) / 2 ** 0.5

    # construct mean
    mean = torch.exp(-d / 0.05)

    # undo softplus transform
    mean = torch.log(torch.exp(mean) - 1.0)
    # plt.pcolor(xx, yy, utils.vector_to_tril(mean, model.n))
    # plt.colorbar()

    return mean


class CorrelatedBayesianHysteresis(BayesianHysteresis):
    def __init__(self, model, n, sigma, use_prior=False):
        super(CorrelatedBayesianHysteresis, self).__init__(model, n)

        self.sigma = sigma
        self.use_prior = use_prior

        self.density = PyroSample(self.get_prior_density_distribution())

        # represent the scale and offset with Normal distributions - priors assume
        # normalized output
        self.scale = PyroSample(dist.Normal(1.0, 1.0))
        self.offset = PyroSample(dist.Normal(0.0, 1.0))

    def get_prior_density_distribution(self):
        # calculate mean
        if self.use_prior:
            prior_mean = calculate_prior_mean(self.hysteresis_model)
        else:
            prior_mean = torch.zeros(self.hysteresis_model.vector_shape).to(
                self.hysteresis_model.h_data)

        # calculate covariance matrix
        corr = calculate_cov(self.hysteresis_model, self.sigma)

        # represent the hysterion density as a correlated multivariate gaussian
        return dist.MultivariateNormal(
            prior_mean,
            covariance_matrix=corr)
