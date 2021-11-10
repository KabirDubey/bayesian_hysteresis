import torch


def sweep_up(h, mesh, initial_state, T=1e-2):
    return torch.minimum(
        initial_state + switch(h, mesh[:, 1], T), torch.ones_like(mesh[:, 1])
    )


def sweep_left(h, mesh, initial_state, T=1e-2):
    return torch.maximum(
        initial_state - switch(mesh[:, 0], h, T), torch.ones_like(mesh[:, 0]) * -1.0
    )


def switch(h, m, T=1e-4):
    return 1.0 + torch.tanh((h - m) / T)


def get_states(
    h: torch.Tensor,
    mesh_points: torch.Tensor,
    tkwargs=None,
    temp=1e-3,
):
    """
    Returns magnetic hysteresis state as an mxnxn tensor, where
    m is the number of distinct applied magnetic fields. The
    states are initially entirely off, and then updated per
    time step depending on both the most recent applied magnetic
    field and prior inputs (i.e. the "history" of the states tensor).

    For each time step, the state matrix is either "swept up" or
    "swept left" based on how the state matrix corresponds to like
    elements in the meshgrid; the meshgrid contains alpha, beta
    coordinates which serve as thresholds for the hysterion state to
    "flip".

    This calculation can be expensive, so we skip recalcuation until if h !=
    current_h

    See: https://www.wolframcloud.com/objects/demonstrations
    /TheDiscretePreisachModelOfHysteresis-source.nb

    Parameters
    ----------
    temp
    tkwargs
    mesh_points
    h : torch.Tensor,
        The applied magnetic field H_1:t={H_1, ... ,H_t}, where
        t represents each time step.

    Raises
    ------
    ValueError
        If n is negative.
    """
    # verify the inputs are in the normalized region
    if not (torch.all(torch.greater_equal(h, torch.zeros(1))) and torch.all(
            torch.less_equal(h, torch.ones(1)))):
        raise RuntimeError('applied values are outside of the unit domain')

    n_mesh_points = mesh_points.shape[0]
    tkwargs = tkwargs or {}

    # list of hysteresis states with initial state set
    initial_state = torch.ones(n_mesh_points, **tkwargs) * -1.0
    states = []

    # loop through the states
    n_calcs = 0
    for i in range(0, len(h)):
        if i == 0:
            # if the new applied field is greater than the old one, sweep up to
            # new applied field
            states += [sweep_up(h[i], mesh_points, initial_state, temp)]
        elif h[i] > h[i - 1]:
            # if the new applied field is greater than the old one, sweep up to
            # new applied field
            states += [sweep_up(h[i], mesh_points, states[i - 1], temp)]
        elif h[i] < h[i - 1]:
            # if the new applied field is less than the old one, sweep left to
            # new applied field
            states += [sweep_left(h[i], mesh_points, states[i - 1], temp)]
        else:
            states += [states[i - 1]]

    # concatenate states into one tensor
    total_states = torch.cat([ele.unsqueeze(0) for ele in states])
    return total_states
