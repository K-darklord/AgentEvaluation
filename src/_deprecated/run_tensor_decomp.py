"""
run_tensor_decomp.py
=====================
Phase 1 (probe): factorize the capability tensor  model x family x axis
(3 x 5 x 6) to check whether latent axes separate L1 (no-tool base) from
L2 (tool-augmented) signal.

Tensor encoding (per docs/ERROR_TAXONOMY.md and RESEARCH_PLAN §5.3):
  defect intensity over the wrong set, where
    - finance   : intensity = 1 - max(T1, T2)   (continuous partial-credit mirror)
    - others    : intensity = 1                  (binary correct/wrong)
    - correct   : 0 on every axis (excluded from the sum -> contribute zero)
  T[m, f, e] = sum of intensity of wrong instances of model m, family f, leaf->axis e.

This is a PROBE (tiny 3x5x6 tensor, 137 wrong instances): results are indicative,
not conclusive. Report factorizations that are cheap and interpretable:
  1. tensor slices (raw)
  2. mode-3 (axis) SVD -> axis loadings + explained variance
  3. PCA on standardized (model*family) x axis -> 2D embedding (L1 vs L2 check)
  4. CP (PARAFAC) rank-2 and rank-3 (numpy ALS) -> per-mode factors
"""
from __future__ import annotations
import json
from pathlib import Path

import numpy as np
import build_capability_matrix as bcm

ROOT = Path(__file__).resolve().parents[1]
WRONG_BANK = ROOT / "experiments" / "error_taxonomy_v2" / "wrong_bank.jsonl"

MODELS = bcm.MODELS
FAMILIES = bcm.FAMILIES
AXES = bcm.MIDDLE_AXES
DIM = bcm.CAPABILITY_DIMENSIONS
L1_FAMILIES = {"math", "math500", "mmlu_pro"}   # no-tool
L2_FAMILIES = {"finance", "bfcl"}               # tool
L1_AXES_HINT = {"computation", "reasoning", "instruction"}  # prior guess, not enforced


def build_tensor():
    T = np.zeros((len(MODELS), len(FAMILIES), len(AXES)))
    n_correct = 0
    for line in open(WRONG_BANK):
        r = json.loads(line)
        m = MODELS.index(r["model"])
        f = FAMILIES.index(r["family"])
        axis = DIM.get(r["error_type"])
        if axis is None:
            continue
        e = AXES.index(axis)
        sig = r.get("signals", {})
        t1 = sig.get("t1"); t2 = sig.get("t2")
        if r["family"] == "finance" and t1 is not None and t2 is not None:
            intensity = 1.0 - max(float(t1), float(t2))
        else:
            intensity = 1.0
        T[m, f, e] += intensity
    return T


def khatri_rao(a, b):
    # column-wise Khatri-Rao: (I*J) x R
    I, R = a.shape
    J, _ = b.shape
    return np.einsum('ir,jr->ijr', a, b).reshape(I * J, R)


def cp_als(T, rank, iters=200, tol=1e-8, seed=0):
    rng = np.random.default_rng(seed)
    I, J, K = T.shape
    A = rng.standard_normal((I, rank))
    B = rng.standard_normal((J, rank))
    C = rng.standard_normal((K, rank))
    T1 = T.reshape(I, -1)
    T2 = np.moveaxis(T, 1, 0).reshape(J, -1)
    T3 = np.moveaxis(T, 2, 0).reshape(K, -1)
    lam = np.ones(rank)
    for it in range(iters):
        # A
        kr = khatri_rao(C, B)
        A = T1 @ kr @ np.linalg.pinv((C.T @ C) * (B.T @ B))
        lam = np.linalg.norm(A, axis=0); lam[lam == 0] = 1e-12
        A = A / lam
        # B
        kr = khatri_rao(C, A)
        B = T2 @ kr @ np.linalg.pinv((C.T @ C) * (A.T @ A))
        lam_b = np.linalg.norm(B, axis=0); lam_b[lam_b == 0] = 1e-12
        B = B / lam_b; lam = lam * lam_b
        # C
        kr = khatri_rao(B, A)
        C = T3 @ kr @ np.linalg.pinv((B.T @ B) * (A.T @ A))
        lam_c = np.linalg.norm(C, axis=0); lam_c[lam_c == 0] = 1e-12
        C = C / lam_c; lam = lam * lam_c
    recon = np.einsum('r,ir,jr,kr->ijk', lam, A, B, C)
    sse = float(np.sum((T - recon) ** 2))
    return lam, A, B, C, sse


def show_var(lam, name):
    v = lam ** 2
    print(f"  {name}: lam={np.round(lam, 3)}  var%={np.round(100 * v / v.sum(), 2)}")


def main():
    T = build_tensor()
    print("=" * 72)
    print("Tensor T[model, family, axis]  (defect intensity sum)")
    print("=" * 72)
    for f, fam in enumerate(FAMILIES):
        print(f"\n[{fam}]")
        hdr = "model".ljust(18) + " ".join(a[:7].rjust(9) for a in AXES)
        print(hdr)
        for m, mdl in enumerate(MODELS):
            row = mdl.ljust(18) + " ".join(f"{T[m, f, e]:9.2f}" for e in range(len(AXES)))
            print(row)

    # ---- mode-3 (axis) SVD ----
    print("\n" + "=" * 72)
    print("Mode-3 (axis) SVD on unfolded (model*family) x axis")
    print("=" * 72)
    X = T.reshape(-1, len(AXES))            # 15 x 6
    U, s, Vt = np.linalg.svd(X, full_matrices=False)
    print(f"  singular values: {np.round(s, 3)}")
    print(f"  explained var %: {np.round(100 * s**2 / np.sum(s**2), 2)}")
    print("\n  axis loadings (V^T rows = components):")
    for r in range(min(3, len(s))):
        print(f"    PC{r+1}: " + ", ".join(f"{a}={Vt[r, i]:+.3f}" for i, a in enumerate(AXES)))

    # ---- PCA 2D embedding (L1 vs L2) ----
    print("\n" + "=" * 72)
    print("PCA 2D embedding of (model, family) rows")
    print("=" * 72)
    Xc = X - X.mean(axis=0)
    Xn = Xc / (X.std(axis=0) + 1e-12)
    _, s2, Vt2 = np.linalg.svd(Xn, full_matrices=False)
    P = Xn @ Vt2[:2].T
    print("  family(L1: math/math500/mmlu_pro | L2: finance/bfcl)")
    for f, fam in enumerate(FAMILIES):
        for m, mdl in enumerate(MODELS):
            tag = "L1" if fam in L1_FAMILIES else "L2"
            print(f"    {fam:<9} {mdl:<18} [{tag}] -> PC=({P[m*len(FAMILIES)+f,0]:+.3f},{P[m*len(FAMILIES)+f,1]:+.3f})")

    # ---- CP rank 2 and 3 ----
    print("\n" + "=" * 72)
    print("CP (PARAFAC) decomposition")
    print("=" * 72)
    for rank in (2, 3):
        lam, A, B, C, sse = cp_als(T, rank)
        print(f"\n[CP rank={rank}]  SSE={sse:.3f}")
        show_var(lam, "weights")
        print("  model factors:")
        for m, mdl in enumerate(MODELS):
            print(f"    {mdl:<18} " + " ".join(f"{A[m, r]:+.3f}" for r in range(rank)))
        print("  family factors:")
        for f, fam in enumerate(FAMILIES):
            print(f"    {fam:<9} " + " ".join(f"{B[f, r]:+.3f}" for r in range(rank)))
        print("  axis factors:")
        for e, a in enumerate(AXES):
            print(f"    {a:<14} " + " ".join(f"{C[e, r]:+.3f}" for r in range(rank)))


if __name__ == "__main__":
    main()
