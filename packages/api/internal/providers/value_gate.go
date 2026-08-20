package providers

import "scouter-ia-api/internal/types"

func EvaluateValueGate(req types.ValueGateRequest) types.ValueGateResponse {
	k := req.KMultiplier
	if k <= 0 {
		k = 1.75
	}

	completenessThreshold := req.CompletenessThreshold
	if completenessThreshold <= 0 {
		completenessThreshold = 0.70
	}

	edge := req.PAdj - req.PFair

	if req.InformationCompleteness < completenessThreshold {
		return types.ValueGateResponse{
			Edge:     edge,
			Decision: "ABSTAIN",
			Reason:   "information completeness below threshold",
		}
	}

	if req.ThinData && abs(edge) < k*req.SeAdj*1.5 {
		return types.ValueGateResponse{
			Edge:     edge,
			Decision: "ABSTAIN",
			Reason:   "thin data with insufficient edge margin",
		}
	}

	threshold := k * req.SeAdj
	if abs(edge) <= threshold {
		return types.ValueGateResponse{
			Edge:     edge,
			Decision: "NOISE",
			Reason:   "edge inside uncertainty band",
		}
	}

	if edge > threshold {
		return types.ValueGateResponse{
			Edge:     edge,
			Decision: "VALUE",
			Reason:   "positive edge above uncertainty band",
		}
	}

	return types.ValueGateResponse{
		Edge:     edge,
		Decision: "ABSTAIN",
		Reason:   "negative edge against market without structural override",
	}
}

func abs(v float64) float64 {
	if v < 0 {
		return -v
	}
	return v
}
