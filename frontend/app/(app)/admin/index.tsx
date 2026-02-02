import React, { useEffect, useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  ActivityIndicator,
  ScrollView,
} from "react-native";
import { fetchAnalyticsSummary, AnalyticsSummary } from "../../../src/api/analytics";

export default function AdminDashboard() {
  const [data, setData] = useState<AnalyticsSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        setLoading(true);
        const res = await fetchAnalyticsSummary();
        setData(res);
        setError(null);
      } catch (e) {
        setError("Erreur lors du chargement des statistiques");
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, []);

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator color="#C62828" />
        <Text style={styles.loadingText}>Chargement des statistiques...</Text>
      </View>
    );
  }

  if (error) {
    return (
      <View style={styles.center}>
        <Text style={styles.error}>{error}</Text>
      </View>
    );
  }

  if (!data) {
    return (
      <View style={styles.center}>
        <Text>Aucune donnée disponible.</Text>
      </View>
    );
  }

  return (
    <ScrollView style={styles.container} contentContainerStyle={{ padding: 16 }}>
      <Text style={styles.title}>Tableau de bord</Text>

      <View style={styles.card}>
        <Text style={styles.cardLabel}>Total des cas de saisie</Text>
        <Text style={styles.cardValue}>{data.total_cases}</Text>
      </View>

      <View style={styles.card}>
        <Text style={styles.cardLabel}>Par espèce</Text>
        {data.by_species.map((item) => (
          <View key={item.species} style={styles.rowBetween}>
            <Text style={styles.rowLabel}>{item.species}</Text>
            <Text style={styles.rowValue}>{item.count}</Text>
          </View>
        ))}
      </View>

      <View style={styles.card}>
        <Text style={styles.cardLabel}>Par motif</Text>
        {data.by_reason.map((item) => (
          <View key={item.reason} style={styles.rowBetween}>
            <Text style={styles.rowLabel}>{item.reason}</Text>
            <Text style={styles.rowValue}>{item.count}</Text>
          </View>
        ))}
      </View>

      <View style={styles.card}>
        <Text style={styles.cardLabel}>Par type de saisie</Text>
        {data.by_seizure_type.map((item) => (
          <View key={item.seizure_type} style={styles.rowBetween}>
            <Text style={styles.rowLabel}>{item.seizure_type}</Text>
            <Text style={styles.rowValue}>{item.count}</Text>
          </View>
        ))}
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#FFFFFF",
  },
  center: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
  },
  loadingText: {
    marginTop: 8,
    color: "#444",
  },
  error: {
    color: "#C62828",
  },
  title: {
    fontSize: 22,
    fontWeight: "700",
    color: "#C62828",
    marginBottom: 16,
  },
  card: {
    backgroundColor: "#F9F9F9",
    borderRadius: 12,
    padding: 12,
    marginBottom: 16,
  },
  cardLabel: {
    fontSize: 16,
    fontWeight: "600",
    marginBottom: 8,
  },
  cardValue: {
    fontSize: 24,
    fontWeight: "700",
    color: "#C62828",
  },
  rowBetween: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginBottom: 4,
  },
  rowLabel: {
    fontSize: 14,
    color: "#444",
  },
  rowValue: {
    fontSize: 14,
    fontWeight: "600",
  },
});
