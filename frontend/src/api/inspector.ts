import { api } from "./client";

export type Species = "bovine" | "ovine" | "caprine" | "porcine" | "camelid" | "other";
export type SeizedPart =
  | "carcass"
  | "liver"
  | "lung"
  | "heart"
  | "kidney"
  | "spleen"
  | "head"
  | "other";
export type SeizureType = "partial" | "total";
export type Unit = "kg" | "g" | "pieces";

export interface CreateSeizurePayload {
  seizure_datetime?: string; // ISO string
  species: Species;
  seized_part: SeizedPart;
  seizure_type: SeizureType;
  reason: string;
  quantity: number;
  unit: Unit;
  notes?: string;
  photos?: string[]; // base64 strings
}

export const createSeizure = async (payload: CreateSeizurePayload) => {
  const res = await api.post("/seizures", payload);
  return res.data;
};

export interface SeizureRecord extends CreateSeizurePayload {
  id: string;
  slaughterhouse_id: string;
  inspector_id: string;
  created_at: string;
  updated_at: string;
}

export interface PaginatedSeizures {
  items: SeizureRecord[];
  total: number;
  page: number;
  page_size: number;
}

export const fetchSeizures = async () => {
  const res = await api.get<PaginatedSeizures>("/seizures");
  return res.data;
};
