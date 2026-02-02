import React from "react";
import { View, Text, StyleSheet } from "react-native";

export default function AdminDashboard() {
  return (
    <View style={styles.container}>
      <Text style={styles.title}>Tableau de bord</Text>
      <Text style={styles.text}>Analytics à implémenter ultérieurement.</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#FFFFFF",
    justifyContent: "center",
    alignItems: "center",
  },
  title: {
    fontSize: 22,
    fontWeight: "700",
    color: "#C62828",
    marginBottom: 12,
  },
  text: {
    fontSize: 16,
    color: "#444",
  },
});
