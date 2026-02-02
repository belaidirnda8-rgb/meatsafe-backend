import { api } from "./client";

export interface AnalyticsSummary {
  total_cases: number;
  by_species: { species: string; count: number }[];
  by_reason: { reason: string; count: number }[];
  by_seizure_type: { seizure_type: string; count: number }[];
}

export const fetchAnalyticsSummary = async (): Promise<AnalyticsSummary> => {
  const res = await api.get<AnalyticsSummary>("/analytics/summary");
  return res.data;
};
