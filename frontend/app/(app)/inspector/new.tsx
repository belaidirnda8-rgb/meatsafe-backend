import React from "react";
import { View, Text, StyleSheet } from "react-native";

export default function NewSeizureScreen() {
  return (
    <View style={styles.container}>
      <Text style={styles.text}>Formulaire de nouvelle saisie (à implémenter)</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
  },
  text: {
    fontSize: 16,
  },
});
