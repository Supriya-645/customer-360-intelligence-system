"""
Shared evaluation utilities - used by both the baseline Logistic Regression
(already trained in notebooks/03_modelling.ipynb) and the model comparison in train.py,
so every candidate model is judged on the same metrics, the same way.

Deliberately NOT optimizing for accuracy: this is a risk problem with ~11:1 class
imbalance, where a model predicting "never defaults" scores ~92% accuracy while
being useless. ROC-AUC and recall on the minority (Defaulted) class are the metrics
that actually matter here.
"""
from dataclasses import dataclass

import numpy as np
from sklearn.metrics import (
    roc_auc_score, roc_curve, precision_score, recall_score, f1_score, confusion_matrix,
)


@dataclass
class EvaluationResult:
    model_name: str
    auc_roc: float
    ks_statistic: float
    precision_defaulted: float
    recall_defaulted: float
    f1_defaulted: float
    confusion_matrix: np.ndarray

    def as_row(self) -> dict:
        return {
            "Model": self.model_name,
            "ROC-AUC": round(self.auc_roc, 4),
            "KS": round(self.ks_statistic, 4),
            "Precision": round(self.precision_defaulted, 4),
            "Recall": round(self.recall_defaulted, 4),
            "F1": round(self.f1_defaulted, 4),
        }


def evaluate_model(model_name: str, y_true, y_pred, y_pred_proba) -> EvaluationResult:
    auc = roc_auc_score(y_true, y_pred_proba)
    fpr, tpr, _ = roc_curve(y_true, y_pred_proba)
    ks = max(tpr - fpr)
    return EvaluationResult(
        model_name=model_name,
        auc_roc=auc,
        ks_statistic=ks,
        precision_defaulted=precision_score(y_true, y_pred, pos_label=1, zero_division=0),
        recall_defaulted=recall_score(y_true, y_pred, pos_label=1, zero_division=0),
        f1_defaulted=f1_score(y_true, y_pred, pos_label=1, zero_division=0),
        confusion_matrix=confusion_matrix(y_true, y_pred),
    )
