import React from "react";
import { View, Text, StyleSheet } from "react-native";
import { useOfflineQueue } from "../store/offlineQueue";

export function NetworkBanner() {
  const { isOnline, items } = useOfflineQueue();

  const pendingCount = items.filter((i) => i.status === "pending").length;

  if (isOnline && pendingCount === 0) {
    return null;
  }

  return (
    <View style={[styles.container, !isOnline && styles.offline]}>
      <Text style={styles.text}>
        {isOnline
          ? `Synchronisation en cours... (${pendingCount} en attente)`
          : "Mode hors-ligne - les saisies seront synchronisées automatiquement"}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    width: "100%",
    paddingVertical: 6,
    paddingHorizontal: 12,
    backgroundColor: "#FFA000",
  },
  offline: {
    backgroundColor: "#C62828",
  },
  text: {
    color: "#FFF",
    fontSize: 12,
    textAlign: "center",
  },
});
