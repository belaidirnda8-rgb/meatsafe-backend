import { api } from "./client";

export interface AnalyticsSummary {
  total_cases: number;
  by_species: { species: string; count: number }[];
  by_reason: { reason: string; count: number }[];
  by_seizure_type: { seizure_type: string; count: number }[];
}

export const fetchAnalyticsSummary = async (
  params?: { start_date?: string; end_date?: string; slaughterhouse_id?: string }
): Promise<AnalyticsSummary> => {
  const res = await api.get<AnalyticsSummary>("/analytics/summary", { params });
  return res.data;
};
