"""
Authors: Zheng Wang, John Griffiths, Andrew Clappison, Hussain Ather, Kevin Kadak
Neural Mass Model fitting
module for cost calculation
"""

import numpy as np  # for numerical operations
from torch import (Tensor as ptTensor, reshape as ptreshape, mean as ptmean, matmul as ptmatmul, transpose as pttranspose, 
                   diag as ptdiag, reciprocal as ptreciprocal, sqrt as ptsqrt, tril as pttril, ones_like as ptones_like, 
                   zeros_like as ptzeros_like, greater as ptgreater, masked_select as ptmasked_select, sum as ptsum, 
                   multiply as ptmultiply, log as ptlog, device as ptdevice)

from ..datatypes import AbstractLoss 
from ..functions.arg_type_check import method_arg_type_check


class CostsFC(AbstractLoss):
    """
    Cost function for Fitting the Functional Connectivity (FC) matrix.
    The cost function is the negative log-likelihood of the Pearson correlation between the simulated FC and empirical FC.

    Attributes
    ----------
    simKey: str
        string key to reference to this const function. i.e., "CostsFC".

    Methods
    -------
    loss: function
        calculates functional connectivity and uses it to calculate the loss
    """
    def __init__(self, simKey=None, model=None):
        """
        Parameters
        ----------
        simKey: str
            type of cost function to be used
        """
        super(CostsFC, self).__init__(simKey =simKey, model = model)
        self.simKey = simKey

    def main_loss(self, simData: dict, empData: ptTensor):
        """Function to calculate the cost function for Functional Connectivity (FC) fitting. It initially calculates the FC matrix using the data from the BOLD time series, makes that mean-zero, and then calculates the Pearson Correlation between the simulated FC and empirical FC. The FC matrix values are then transposed to the 0-1 range. We then use this FC matrix as a probability matrix and use it to get the cross-entropy-like loss using negative log likelihood.

        Parameters
        ----------
        simData: dict of torch.Tensor with node_size X datapoint
            simulated BOLD
        empData: torch.Tensor with node_size X datapoint
            empirical BOLD

        Returns
        -------
        losses_corr: torch.tensor
            cost function value
        """
        method_arg_type_check(self.main_loss) # Check that the passed arguments (excluding self) abide by their expected data types
        
        sim = simData[self.simKey]
        
        logits_series_tf = sim
        labels_series_tf = empData
        # get node_size() and TRs_per_window()
        node_size = logits_series_tf.shape[0]
        truncated_backprop_length = logits_series_tf.shape[1]

        # remove mean across time
        labels_series_tf_n = labels_series_tf - ptreshape(ptmean(labels_series_tf, 1),
                                                          [node_size, 1])  # - torch.matmul(

        logits_series_tf_n = logits_series_tf - ptreshape(ptmean(logits_series_tf, 1),
                                                          [node_size, 1])  # - torch.matmul(

        # correlation
        cov_sim = ptmatmul(logits_series_tf_n, pttranspose(logits_series_tf_n, 0, 1))
        cov_def = ptmatmul(labels_series_tf_n, pttranspose(labels_series_tf_n, 0, 1))

        # Getting the FC matrix for the simulated and empirical BOLD signals
        FC_sim_T = ptmatmul(ptmatmul(ptdiag(ptreciprocal(ptsqrt(
            ptdiag(cov_sim)))), cov_sim),
            ptdiag(ptreciprocal(ptsqrt(ptdiag(cov_sim))))) # SIMULATED FC
        FC_T = ptmatmul(ptmatmul(ptdiag(ptreciprocal(ptsqrt(ptdiag(cov_def)))), cov_def),
                        ptdiag(ptreciprocal(ptsqrt(ptdiag(cov_def))))) # EMPIRICAL FC

        # Masking out the upper triangle of the FC matrix and keeping the lower triangle
        ones_tri = pttril(ptones_like(FC_T), -1)
        zeros = ptzeros_like(FC_T)  # create a tensor all ones
        mask = ptgreater(ones_tri, zeros)  # boolean tensor, mask[i] = True iff x[i] > 1

        FC_tri_v = ptmasked_select(FC_T, mask)
        FC_sim_tri_v = ptmasked_select(FC_sim_T, mask)

        # Bring the FC mean to zero
        FC_v = FC_tri_v - ptmean(FC_tri_v)
        FC_sim_v = FC_sim_tri_v - ptmean(FC_sim_tri_v)

        # Calculate the correlation coefficient between the simulated FC and empirical FC
        corr_FC = ptsum(ptmultiply(FC_v, FC_sim_v)) \
                  * ptreciprocal(ptsqrt(ptsum(ptmultiply(FC_v, FC_v)))) \
                  * ptreciprocal(ptsqrt(ptsum(ptmultiply(FC_sim_v, FC_sim_v))))

        # Bringing the corr-FC to the 0-1 range, and calculating the negative log-likelihood
        losses_corr = -ptlog(0.5000 + 0.5 * corr_FC)  # ptmean((FC_v -FC_sim_v)**2)#
        return losses_corr



class CostsFixedFC(AbstractLoss):
    """
    Cost function for Fitting the Functional Connectivity (FC) matrix.
    In this version, the empirical FC is given directly, instead of being given an empirical time series. 
    The cost function is the negative log-likelihood of the Pearson correlation between the simulated FC and empirical FC. 

    Has GPU support.

    Attributes
    ----------
    simKey: str
        string key to reference to this const function. i.e., "CostsFC".
    device: torch.device
        Whether to run on GPU or CPU
    Methods:
    --------
    loss: function
        calculates functional connectivity and uses it to calculate the loss
    """
    def __init__(self, simKey, device = ptdevice('cpu')):
        """
        Parameters
        ----------
        simKey: str
            The state variable or output variable from the model used for the simulated FC
        device: torch.device
            Whether to run on GPU or CPU
        """
        super(CostsFixedFC, self).__init__()
        self.simKey = simKey
        self.device = device

    def loss(self, simData, empData):
        """Function to calculate the cost function for Functional Connectivity (FC) fitting. 
        It initially calculates the FC matrix using the data from the time series, 
        makes that mean-zero, and then calculates the Pearson Correlation between the simulated FC and empirical FC. 
        The FC matrix values are then transposed to the 0-1 range. 
        We then use this FC matrix as a probability matrix and use it to get the cross-entropy-like loss using negative log likelihood.

        Parameters
        ----------
        simData: dict of torch.tensor with node_size X time_point
            Simulated Time Series 
        empData: torch.tensor with node_size X node_size
            Empirical Functional Connectivity

        Returns
        -------
        losses_corr: torch.tensor
            cost function value
        """
        simTS = simData[self.simKey]
        empFC = empData
        
        logits_series_tf = simTS

        # get node_size() and TRs_per_window()
        node_size = logits_series_tf.shape[0]
        truncated_backprop_length = logits_series_tf.shape[1]

        # remove mean across time
        logits_series_tf_n = logits_series_tf - ptreshape(ptmean(logits_series_tf, 1), [node_size, 1])

        # correlation
        cov_sim = ptmatmul(logits_series_tf_n, pttranspose(logits_series_tf_n, 0, 1))

        # Getting the FC matrix for the simulated and empirical BOLD signals
        FC_sim_T = ptmatmul(ptmatmul(ptdiag(ptreciprocal(ptsqrt(ptdiag(cov_sim)))), cov_sim),
                                             ptdiag(ptreciprocal(ptsqrt(ptdiag(cov_sim))))) # SIMULATED FC

        # Masking out the upper triangle of the FC matrix and keeping the lower triangle
        ones_tri = pttril(ptones_like(empFC).to(self.device), -1)
        zeros = ptzeros_like(empFC).to(self.device)  # create a tensor all ones
        mask = ptgreater(ones_tri, zeros)  # boolean tensor, mask[i] = True iff x[i] > 1

        FC_tri_v = ptmasked_select(empFC, mask)
        FC_sim_tri_v = ptmasked_select(FC_sim_T, mask)

        # Bring the FC mean to zero
        FC_v = FC_tri_v - ptmean(FC_tri_v)
        FC_sim_v = FC_sim_tri_v - ptmean(FC_sim_tri_v)

        # Calculate the correlation coefficient between the simulated FC and empirical FC
        corr_FC = ptsum(ptmultiply(FC_v, FC_sim_v)) \
                  * ptreciprocal(ptsqrt(ptsum(ptmultiply(FC_v, FC_v)))) \
                  * ptreciprocal(ptsqrt(ptsum(ptmultiply(FC_sim_v, FC_sim_v))))

        # Bringing the corr-FC to the 0-1 range, and calculating the negative log-likelihood
        losses_corr = -ptlog(0.5000 + 0.5 * corr_FC) 
        
        return losses_corr     
