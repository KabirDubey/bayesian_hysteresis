from torchAccelerator.hysteresis import HysteresisQuad, HysteresisAccelerator
from torchAccelerator.first_order import TorchQuad, TorchDrift, TorchAccelerator
from hysteresis.base import TorchHysteresis
from hysteresis.visualization import plot_hysteresis_density
import torch
import matplotlib.pyplot as plt


def density_function(mesh_pts):
    x = mesh_pts[:, 0]
    y = mesh_pts[:, 1]
    return torch.exp(-(y - x) / 0.5)


class TestHysteresisQuad:
    def test_quad_grad(self):
        Q = TorchQuad("q1", torch.tensor(1.0), torch.tensor(1.0))
        M = Q.forward()
        M[0, 0].backward()
        assert Q.K1.grad == -torch.sin(torch.tensor(1.0)) / 2.0

        new_tensor = torch.tensor(-0.5, requires_grad=True)
        M = Q.get_matrix(new_tensor)
        M[1, 0].backward()
        assert torch.isclose(new_tensor.grad, torch.tensor(-1.173), atol=1e-4)

        new_tensor = torch.tensor(-100.5, requires_grad=True)
        M = Q.get_matrix(new_tensor)
        M[0, 0].backward()

    def test_hysteresis_quad(self):
        with torch.autograd.detect_anomaly():
            h_data = torch.linspace(0, 1.0, 10)
            H = TorchHysteresis(h_data, mesh_scale=0.1)
            HQ = HysteresisQuad("Q1", torch.tensor(1.0), H, scale=torch.tensor(1.0))

            # test gradient for calculating the transport matrix from magnetization
            x = torch.tensor(0.5, requires_grad=True)
            matrix = HQ._calculate_beam_matrix(x)
            matrix[0, 0].backward()
            assert not torch.isnan(x.grad)

            x = torch.tensor(0.0, requires_grad=True)
            matrix = HQ._calculate_beam_matrix(x)
            matrix[0, 0].backward()
            assert not torch.isnan(x.grad)

            x = torch.tensor(-0.5, requires_grad=True)
            matrix = HQ._calculate_beam_matrix(x)
            matrix[0, 0].backward()
            assert not torch.isnan(x.grad)

            # test calculating magnetization
            x = torch.tensor(0.0, requires_grad=True)
            m = HQ.hysteresis_model.predict_magnetization(h=x)
            m[0].backward()
            assert not torch.isnan(x.grad)

            # test gradient for calculating the transport matrix from applied field
            x = torch.tensor(0.2, requires_grad=True)
            matrix = HQ.get_transport_matrix(x)
            matrix[0, 0].backward()
            assert not torch.isnan(x.grad)

            HQ.fantasy_H.data = torch.tensor(0.5)
            matrix = HQ.forward()
            matrix[1, 0].backward()
            assert not torch.isnan(HQ.fantasy_H.grad)
            auto_diff_grad = HQ.fantasy_H.grad.clone()

            # check against numerical gradient
            dx = torch.tensor(0.0001)
            HQ.fantasy_H.data = torch.tensor(0.5) + dx
            matrix_dx = HQ.forward()
            approx = (matrix_dx[1, 0] - matrix[1, 0]) / dx
            assert torch.isclose(auto_diff_grad, approx, rtol=0.05)
            # values = torch.linspace(0.0, 1.0, 100)
            # bs = []
            # bs_grad = []
            #
            # for ele in values:
            #     # NOTE: Don't forget that gradients accumulate!!###########
            #     HQ.fantasy_H.grad.zero_()
            #     HQ.fantasy_H.data = ele
            #     matrix = HQ.forward()
            #     matrix[1, 0].backward()
            #     bs += [matrix[1, 0].detach()]
            #     bs_grad += [HQ.fantasy_H.grad.clone()]
            #
            # plt.plot(values, bs_grad)
            # plt.figure()
            # plt.plot(values, bs)
            # idx = 50
            # print(f"grad_loc:{values[idx]}")
            # grad_approx = (bs[idx] - bs[idx - 1]) / (values[idx] - values[idx - 1])
            # print(f"grad_approx:{grad_approx}")
            # print(f"torch_grad:{bs_grad[idx]}")
            # plt.show()
