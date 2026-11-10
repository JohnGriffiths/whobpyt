"""
.. _ex-getting-started:

========================================================
Getting started: simulate and fit a whole-brain model
========================================================

This tutorial walks through the core WhoBPyT workflow on a small toy network,
so it runs in a minute or two on a laptop CPU and needs no data downloads.

The purpose is to show the mechanics of simulation and gradient-based fitting
in a very quick demo. The random anatomy, low-noise dynamics, and synthetic
target are deliberately simplified: this is not a neurobiologically realistic
example, nor evidence that a fitted model explains real brain responses.

You will:

1. build a toy connectome (structural connectivity, distances, and a lead field),
2. define Jansen-Rit neural mass model parameters, including which ones are learnable,
3. simulate a stimulus-evoked EEG response, and
4. fit a model to that EEG response using gradient descent.

The same steps, applied to real TMS-EEG data, are shown in
:ref:`ex-tmseeg` and in the paper replications in the
:ref:`examples gallery <examples-gallery>`.
For real anatomy but still synthetic fitting targets, continue with
:ref:`ex-getting-started-connectome`, which explores alternative stimulation
sites and evoked-response propagation on the Momi 2023 connectome.
"""

# %%
# Imports
# -------
#
# The pieces you need from WhoBPyT are:
#
# * :class:`~whobpyt.datatypes.Parameter` for defining model
#   parameters and their priors,
# * :class:`~whobpyt.datatypes.Timeseries` for holding
#   empirical (or simulated) recordings,
# * :class:`~whobpyt.models.jansen_rit.JansenRitModel` and its
#   parameter container ``JansenRitParams``,
# * a cost function, here ``CostsJR``, and
# * :class:`~whobpyt.run.ModelFitting`, which runs the
#   simulation and training loops.

import numpy as np
import torch
import matplotlib.pyplot as plt

from whobpyt.datatypes import Parameter as par, Timeseries
from whobpyt.models.jansen_rit import JansenRitModel, JansenRitParams
from whobpyt.optimization.custom_cost_JR import CostsJR
from whobpyt.run import ModelFitting

# Make the tutorial reproducible
rng = np.random.default_rng(42)
np.random.seed(42)
torch.manual_seed(42)

# sphinx_gallery_thumbnail_number = 2

# %%
# 1. Build a toy connectome
# -------------------------
#
# A whole-brain model needs:
#
# * a **structural connectivity** (SC) matrix, which sets the connection
#   strength between brain regions (nodes),
# * a **distance** matrix, which sets the conduction delays between regions,
# * a **lead field** matrix, which maps region (source) activity onto
#   EEG channels.
#
# In real analyses these come from diffusion MRI tractography, a brain
# parcellation, and an EEG head model. Here we make random ones.

n_nodes = 20      # number of brain regions
n_chans = 16      # number of EEG channels

# Random region coordinates (mm) -> Euclidean distance matrix
coords = rng.uniform(-60, 60, size=(n_nodes, 3))
dist = np.linalg.norm(coords[:, None, :] - coords[None, :, :], axis=-1)

# Sparse, symmetric, log-scaled and normalized SC matrix
sc = rng.random((n_nodes, n_nodes)) * (rng.random((n_nodes, n_nodes)) < 0.3)
sc = (sc + sc.T) / 2
np.fill_diagonal(sc, 0)
sc = np.log1p(sc) / np.linalg.norm(np.log1p(sc))

# Random lead field (channels x regions)
lm = rng.normal(0, 0.1, size=(n_chans, n_nodes))

fig, axs = plt.subplots(1, 3, figsize=(11, 3.2))
for ax, mat, title in zip(axs, [sc, dist, lm],
                          ['Structural connectivity', 'Distance (mm)',
                           'Lead field']):
    im = ax.imshow(mat, cmap='viridis')
    ax.set_title(title)
    fig.colorbar(im, ax=ax, shrink=0.8)
axs[0].set_xlabel('Region'); axs[0].set_ylabel('Region')
axs[1].set_xlabel('Region')
axs[2].set_xlabel('Region'); axs[2].set_ylabel('Channel')
fig.tight_layout()

# %%
# 2. Define the model parameters
# ------------------------------
#
# Every model parameter is a :class:`~whobpyt.datatypes.Parameter`.
# Its arguments are ``par(value, prior_mean, prior_std, fit_par, asLog)``:
#
# * ``par(3.25)`` is a **fixed** parameter.
# * ``par(100, 100, 2, True)`` is a **learnable** parameter with a Gaussian
#   prior (mean 100, standard deviation 2). Its starting value is drawn from
#   the prior.
# * ``asLog=True`` stores the log of the value so that it stays positive.
#
# ``ki`` sets which regions receive the external stimulus; here only
# region 0 is stimulated. We use moderate coupling and low input noise so
# the network returns to its resting state after a brief perturbation.
# Only three parameters are fitted; anatomy and observation scaling stay
# fixed, making this small inverse problem easier to interpret.

ki0 = np.zeros((n_nodes, 1))
ki0[0] = 1


def make_params(fit=False):
    """Known generating parameters, or an intentionally offset fitting model."""
    return JansenRitParams(
        A=par(3.25),
        a=par(85 if fit else 100, 100, 20, fit, asRand=False),
        B=par(22),
        b=par(60 if fit else 50, 50, 10, fit, asRand=False),
        g=par(80 if fit else 100, 100, 20, fit, asRand=False),
        g_f=par(10), g_b=par(10),
        c1=par(135), c2=par(135 * 0.8),
        c3=par(135 * 0.25), c4=par(135 * 0.25),
        std_in=par(1),
        vmax=par(5), v0=par(6), r=par(0.56),
        y0=par(0), mu=par(1.5), k=par(5), cy0=par(50),
        ki=par(ki0), lm=par(lm),
    )


# %%
# 3. Create the model and simulate an evoked response
# ---------------------------------------------------
#
# The model integrates the neural mass equations with a step of
# ``step_size`` seconds and outputs EEG every ``tr`` seconds. Simulation and
# training run in windows of ``TRs_per_window`` output samples.
#
# The stimulus ``u`` has shape ``(regions, integration steps per sample,
# samples)``. We deliver a 5 ms pulse after a 100 ms prestimulus baseline.
# The regional weights ``ki`` restrict it to region 0. Unlike the sustained
# drive used in some fitting examples, this short input lets us see the
# network's response *after* the pulse has ended.

step_size = 0.0001        # integration step (s)
tr = 0.001                # output sampling interval (s), i.e. 1000 Hz
TRs_per_window = 20       # output samples per window
n_samples = 600           # 100 ms baseline and 500 ms after stimulus onset
steps_per_sample = int(tr / step_size)
stim_onset = 100
pulse_samples = 5
n_trials = 8
times_ms = (np.arange(n_samples) - stim_onset) * tr * 1000


def make_model(fit=False):
    return JansenRitModel(make_params(fit=fit), node_size=n_nodes,
                          TRs_per_window=TRs_per_window, step_size=step_size,
                          output_size=n_chans, tr=tr, sc=sc, lm=lm, dist=dist,
                          use_fit_gains=False, use_fit_lfm=False)


u = np.zeros((n_nodes, steps_per_sample, n_samples))
u[:, :, stim_onset:stim_onset + pulse_samples] = 100


def simulate_trials(model, stimulus, num_trials=n_trials):
    """Settle the model, then simulate repeated epochs with independent noise."""
    recordings = {name: [] for name in ['eeg', 'E', 'I', 'P']}
    with torch.no_grad():
        state = model.createIC(ver=0)
        history = model.createDelayIC(ver=0)
        resting_input = torch.zeros(n_nodes, steps_per_sample, TRs_per_window)
        for _ in range(100):
            output, history = model(resting_input, state, history)
            state = output['current_state']
        resting_state, resting_history = state.clone(), history.clone()

        for _ in range(num_trials):
            state, history = resting_state.clone(), resting_history.clone()
            windows = {name: [] for name in recordings}
            for start in range(0, n_samples, TRs_per_window):
                external = torch.tensor(
                    stimulus[:, :, start:start + TRs_per_window], dtype=torch.float32)
                output, history = model(external, state, history)
                state = output['current_state']
                for name in windows:
                    windows[name].append(output[name].numpy())
            for name in recordings:
                recordings[name].append(np.concatenate(windows[name], axis=1))
    return {name: np.stack(trials) for name, trials in recordings.items()}


def baseline_correct(data):
    """Subtract each channel's (or region's) prestimulus mean."""
    return data - data[..., :stim_onset].mean(axis=-1, keepdims=True)


def mark_stimulus(ax):
    ax.axhline(0, color='0.8', lw=0.7)
    ax.axvspan(0, pulse_samples * tr * 1000, color='0.5', alpha=0.2)
    ax.axvline(0, color='0.3', lw=0.8, ls='--')
    ax.set_xlim(times_ms[0], times_ms[-1])
    ax.set_xlabel('Time from stimulus (ms)')

ref_model = make_model()
target_trials = simulate_trials(ref_model, u)
eeg_target = target_trials['eeg'].mean(axis=0)
evoked = baseline_correct(eeg_target)
gfp = np.sqrt(np.mean(evoked ** 2, axis=0))
peak_sample = stim_onset + np.argmax(gfp[stim_onset:])
peak_channel = np.argmax(np.abs(evoked[:, peak_sample]))
channel_colors = plt.cm.coolwarm(np.linspace(0.05, 0.95, n_chans))

# %%
# An evoked response is the **trial average**, not an arbitrary single noisy
# trajectory. We first allow two seconds of settling, then average eight
# trials with independent input noise. Baseline correction is applied for
# display only; fitting below uses the uncorrected model output.
#
# The right panel shows global field power (GFP): the root-mean-square
# voltage across the average-referenced channels. This avoids cancellation
# between positive and negative sensors. There is no temporal filtering or
# hand-crafted response template here: the waveform comes from the model.
# With a random toy connectome and lead field, these are illustrative
# dynamics, not predictions of specific human TMS-EEG components.

fig, axs = plt.subplots(1, 2, figsize=(11, 3.8))
for channel, color in enumerate(channel_colors):
    axs[0].plot(times_ms, evoked[channel], color=color, lw=1, alpha=0.8)
axs[0].set(title=f'Evoked EEG ({n_trials}-trial average)', ylabel='EEG (a.u.)')
single_trials = baseline_correct(target_trials['eeg'])
for trial in single_trials:
    axs[1].plot(times_ms, trial[peak_channel], color='0.7', lw=0.6, alpha=0.4)
axs[1].plot(times_ms, evoked[peak_channel], color='tab:blue', lw=2,
            label=f'Channel {peak_channel}: average')
axs[1].plot(times_ms, gfp, color='black', lw=1.5, label='Global field power')
axs[1].set(title='Single trials and stimulus-locked response', ylabel='EEG (a.u.)')
axs[1].legend(loc='upper right', fontsize=8)
for ax in axs:
    mark_stimulus(ax)
fig.tight_layout()

# %%
# The EEG is a projection of ``E - I``, the net postsynaptic potential
# entering the pyramidal population, not the state variable ``P`` itself.
# Plotting this source signal connects the sensor response to local and
# network activity. Only the red region receives direct stimulation;
# responses elsewhere arise through the connectome.

source_evoked = baseline_correct(
    (target_trials['E'] - target_trials['I']).mean(axis=0))
fig, ax = plt.subplots(figsize=(8, 3.5))
ax.plot(times_ms, source_evoked[1:].T, lw=1, color='tab:blue', alpha=0.4)
ax.plot(times_ms, source_evoked[0], lw=2, color='tab:red', label='Stimulated region')
ax.set(ylabel='Change in E - I (mV)', title='Source response: local drive and network propagation')
mark_stimulus(ax)
ax.legend(loc='upper right')
fig.tight_layout()

# %%
# 4. Fit a model to the EEG
# -------------------------
#
# Now treat the simulated EEG as if it were an empirical recording and fit a
# **new** model to it. Its synaptic rates ``a`` and ``b`` and coupling ``g``
# start away from the known generating values. We retain the initial
# prediction so that improvement is visible, rather than only showing a
# target and a final prediction.
#
# :meth:`~whobpyt.run.ModelFitting.train` runs the model
# window by window, compares each simulated window with the matching
# empirical window using the cost function, and updates the learnable
# parameters by back-propagating through time.
#
# We run only a handful of epochs to keep the tutorial fast. This is a
# controlled synthetic-data fit with known anatomy, not a demonstration of
# unique parameter recovery. Real analyses need more data and validation.

emp = Timeseries(eeg_target, tr)

model = make_model(fit=True)
fit = ModelFitting(model, CostsJR(model))
initial_trials = simulate_trials(model, u)
eeg_initial = initial_trials['eeg'].mean(axis=0)
fit.train(u=u, empRecs=[emp], num_epochs=5, TPperWindow=TRs_per_window,
          warmupWindow=20, learningrate=0.5, lr_2ndLevel=0.01)

# %%
# ``fit.trainingStats`` keeps the loss and the learnable parameter values
# after every epoch, which is useful for checking convergence. With so few
# epochs the loss need not decrease monotonically: parameters are updated
# within each epoch, and each simulated training epoch has new input noise.

fig, axs = plt.subplots(1, 2, figsize=(10, 3.5))
axs[0].plot(np.arange(1, len(fit.trainingStats.loss) + 1),
            fit.trainingStats.loss, 'o-')
axs[0].set(xlabel='Epoch', ylabel='Loss', title='Training loss')
for name in ['a', 'b', 'g']:
    vals = np.array(fit.trainingStats.fit_params[name]).ravel()
    axs[1].plot(np.arange(1, len(vals) + 1), vals / vals[0], 'o-', label=name)
axs[1].set(xlabel='Epoch', ylabel='Value / initial value',
           title='Learnable parameters')
axs[1].legend()
fig.tight_layout()

# %%
# Finally, compare trial-averaged predictions before and after fitting.
# RMSE is computed on the raw EEG across **all** channels and samples,
# while the overlay uses the channel selected from the target above.

fitted_trials = simulate_trials(model, u)
eeg_fit = fitted_trials['eeg'].mean(axis=0)
initial_rmse = np.sqrt(np.mean((eeg_initial - eeg_target) ** 2))
fitted_rmse = np.sqrt(np.mean((eeg_fit - eeg_target) ** 2))
print(f'All-channel RMSE: {initial_rmse:.2f} before, {fitted_rmse:.2f} after fitting')

fig, axs = plt.subplots(1, 2, figsize=(11, 3.8))
axs[0].plot(times_ms, evoked[peak_channel], color='black', lw=2, label='Target')
axs[0].plot(times_ms, baseline_correct(eeg_initial)[peak_channel],
            color='0.5', lw=1.5, ls='--', label='Before fitting')
axs[0].plot(times_ms, baseline_correct(eeg_fit)[peak_channel],
            color='tab:red', lw=1.5, label='After fitting')
axs[0].set(title=f'Channel {peak_channel}', ylabel='EEG (a.u.)')
axs[0].legend(fontsize=8)
for data, color, label in [(evoked, 'black', 'Target'),
                            (baseline_correct(eeg_initial), '0.5', 'Before fitting'),
                            (baseline_correct(eeg_fit), 'tab:red', 'After fitting')]:
    axs[1].plot(times_ms, np.sqrt(np.mean(data ** 2, axis=0)),
                color=color, lw=1.5, label=label)
axs[1].set(title=f'All-channel RMSE: {initial_rmse:.2f} to {fitted_rmse:.2f}',
           ylabel='Global field power (a.u.)')
axs[1].legend(fontsize=8)
for ax in axs:
    mark_stimulus(ax)
fig.tight_layout()

# %%
# Saving results
# --------------
#
# The whole fitting object, including the trained model and training
# history, can be saved with ``fit.save('my_fit.pkl')`` and reloaded with
# :mod:`pickle`.
#
# Next steps
# ----------
#
# * :ref:`ex-tmseeg` applies this workflow to real TMS-EEG data, with a real
#   connectome and lead field.
# * The :doc:`/documentation/usage/cookbook` has short recipes for common tasks.
# * The :doc:`/documentation/api/index` documents every class used above.
