"""Hierarchical (network-level) Bayesian filter.

Charging stations usually report through a shared charging station management
system (CSMS). If that system is compromised, several stations can lie at once;
a local equipment or reporting fault, by contrast, affects one station.

The filter tracks, jointly and exactly,

    G         in {0, 1}           is the shared reporting network compromised?
    H_1..H_J  in {N, C, F, A}     the explanation at each station

with the joint belief b(G, H_1, ..., H_J) (2 x 4^J states; 512 for 4 stations).

Transition model (per minute):
    G:   stays compromised / uncompromised with high probability
    H_j: given G = 0, an attack at a single station is rare (a local attack is
         still possible); given G = 1, stations are likely to move into A.
         Explanations otherwise stay put, with small switching probabilities.

Observation model: the same per-station likelihoods as the independent filter
(hypotheses.py). An observation at station j multiplies the joint belief along
station j's axis, so evidence at one station changes the belief about G, and
through G the belief about every other station. Honest-looking evidence at the
other stations (changing, non-jammed reports; consistent arrivals) pushes back,
so a single lying station can also be explained as a local attack.
"""
import math

import numpy as np

from .hypotheses import HYPS, PRIOR, STAY, arrival_likelihood, disc_bin, stream_likelihood, verify_likelihood

A = HYPS.index("A")


def station_transition(g):
    """4x4 matrix T[from, to] for one station, given the network state g."""
    T = np.zeros((4, 4))
    if g == 0:
        into_a, leave_a = 0.0005, 0.005       # local attacks are rare and may end
    else:
        into_a, leave_a = 0.01, 0.0005        # a compromised network spreads to stations
    for i in range(4):
        if i == A:
            T[i, i] = 1 - leave_a
            T[i, HYPS.index("N")] = leave_a
            continue
        T[i, A] = into_a
        other = [k for k in range(4) if k not in (i, A)]
        switch = (1 - STAY) / len(other)
        for k in other:
            T[i, k] = switch
        T[i, i] = 1 - into_a - switch * len(other)
    return T


class NetworkBelief:
    def __init__(self, stations, p_compromised=0.01, g_on=0.0005, g_off=0.001, surprise_alpha=0.3):
        self.stations = list(stations)
        self.J = len(self.stations)
        self.idx = {s: i for i, s in enumerate(self.stations)}
        self.TG = np.array([[1 - g_on, g_on], [g_off, 1 - g_off]])
        self.T = [station_transition(0), station_transition(1)]
        prior0 = np.array([PRIOR[k] for k in HYPS])
        prior1 = prior0.copy()
        prior1[A] = 0.5
        prior1 /= prior1.sum()
        b = np.zeros((2,) + (4,) * self.J)
        for g, (pg, pr) in enumerate(((1 - p_compromised, prior0), (p_compromised, prior1))):
            joint = pg
            for _ in range(self.J):
                joint = np.multiply.outer(joint, pr)
            b[g] = joint
        self.b = b / b.sum()
        self.alpha = surprise_alpha
        self.surprise = {s: 0.0 for s in self.stations}
        self.n_obs = {s: 0 for s in self.stations}

    def predict(self):
        new = np.zeros_like(self.b)
        for g2 in (0, 1):
            tmp = self.TG[0, g2] * self.b[0] + self.TG[1, g2] * self.b[1]
            for j in range(self.J):
                tmp = np.moveaxis(np.tensordot(tmp, self.T[g2], axes=([j], [0])), -1, j)
            new[g2] = tmp
        self.b = new / new.sum()

    def _update(self, station, lik):
        j = self.idx[station]
        v = np.array([lik[k] for k in HYPS])
        shape = [1] * (self.J + 1)
        shape[j + 1] = 4
        post = self.b * v.reshape(shape)
        pred = post.sum()
        self.b = post / pred
        s = -math.log(max(pred, 1e-12))
        self.surprise[station] = (1 - self.alpha) * self.surprise[station] + self.alpha * s
        self.n_obs[station] += 1
        return pred

    def observe_arrival(self, station, reported_avail, observed_avail, report_extreme):
        return self._update(station, arrival_likelihood(reported_avail, observed_avail, report_extreme))

    def observe_stream(self, station, changed, jammed=False):
        return self._update(station, stream_likelihood(changed, jammed))

    def observe_verification(self, station, reported_avail, observed_avail):
        return self._update(station, verify_likelihood(disc_bin(reported_avail - observed_avail)))

    def marginal(self, station):
        j = self.idx[station]
        axes = tuple(a for a in range(self.J + 1) if a != j + 1)
        m = self.b.sum(axis=axes)
        return {k: float(m[i]) for i, k in enumerate(HYPS)}

    def p_compromised(self):
        return float(self.b[1].sum())


class StationView:
    """Gives one station's marginal belief the same interface as StationBelief."""

    def __init__(self, net, station):
        self.net, self.s = net, station

    @property
    def b(self):
        return self.net.marginal(self.s)

    @property
    def surprise(self):
        return self.net.surprise[self.s]

    @property
    def n_obs(self):
        return self.net.n_obs[self.s]

    def reliable(self):
        b = self.b
        return b["N"] + b["C"]

    def inadequate(self, threshold):
        return self.n_obs >= 3 and self.surprise > threshold
