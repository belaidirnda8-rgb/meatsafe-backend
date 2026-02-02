import React, { useEffect, useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  ActivityIndicator,
} from "react-native";
import { fetchSeizures, SeizureRecord } from "../../../src/api/inspector";

export default function AdminSeizures() {
  const [data, setData] = useState<SeizureRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    try {
      setLoading(true);
      const res = await fetchSeizures();
      setData(res.items || []);
      setError(null);
    } catch (e) {
      setError("Erreur lors du chargement des saisies");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const renderItem = ({ item }: { item: SeizureRecord }) => (
    <View style={styles.item}>
      <Text style={styles.itemTitle}>
        {item.species} - {item.seized_part} ({item.seizure_type})
      </Text>
      <Text style={styles.itemSubtitle}>Motif: {item.reason}</Text>
      <Text style={styles.itemSubtitle}>
        Quantité: {item.quantity} {item.unit}
      </Text>
    </View>
  );

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator color="#C62828" />
        <Text style={styles.loadingText}>Chargement des saisies...</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {error && <Text style={styles.error}>{error}</Text>}
      <FlatList
        data={data}
        keyExtractor={(item) => item.id}
        renderItem={renderItem}
        contentContainerStyle={{ padding: 16, paddingBottom: 32 }}
        ListEmptyComponent={
          !loading ? (
            <View style={styles.center}>
              <Text>Aucune saisie pour le moment.</Text>
            </View>
          ) : null
        }
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#FFFFFF",
  },
  center: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
  },
  loadingText: {
    marginTop: 8,
    color: "#444",
  },
  error: {
    color: "#C62828",
    marginTop: 8,
    textAlign: "center",
  },
  item: {
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: "#EEE",
  },
  itemTitle: {
    fontSize: 16,
    fontWeight: "600",
  },
  itemSubtitle: {
    fontSize: 14,
    color: "#555",
  },
});
