import React, { useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  TextInput,
  TouchableOpacity,
  ScrollView,
  KeyboardAvoidingView,
  Platform,
  ActivityIndicator,
  Alert,
} from "react-native";
import * as ImagePicker from "expo-image-picker";
import { useRouter } from "expo-router";
import {
  createSeizure,
  Species,
  SeizedPart,
  SeizureType,
  Unit,
} from "../../src/api/inspector";

const MAX_PHOTOS = 3;

const SPECIES_OPTIONS: { label: string; value: Species }[] = [
  { label: "Bovin", value: "bovine" },
  { label: "Ovin", value: "ovine" },
  { label: "Caprin", value: "caprine" },
  { label: "Porcin", value: "porcine" },
  { label: "Camelidé", value: "camelid" },
  { label: "Autre", value: "other" },
];

const PART_OPTIONS: { label: string; value: SeizedPart }[] = [
  { label: "Carcasse entière", value: "carcass" },
  { label: "Foie", value: "liver" },
  { label: "Poumons", value: "lung" },
  { label: "Cœur", value: "heart" },
  { label: "Reins", value: "kidney" },
  { label: "Rate", value: "spleen" },
  { label: "Tête", value: "head" },
  { label: "Autre", value: "other" },
];

const SEIZURE_TYPE_OPTIONS: { label: string; value: SeizureType }[] = [
  { label: "Partielle", value: "partial" },
  { label: "Totale", value: "total" },
];

const UNIT_OPTIONS: { label: string; value: Unit }[] = [
  { label: "kg", value: "kg" },
  { label: "g", value: "g" },
  { label: "Pièces", value: "pieces" },
];

// Pour MVP, liste simple de raisons (à affiner plus tard)
const REASON_OPTIONS: string[] = [
  "Tuberculose",
  "Parasites",
  "Contamination",
  "Lésion locale",
  "Autre",
];

export default function NewSeizureScreen() {
  const router = useRouter();

  const [species, setSpecies] = useState<Species | null>(null);
  const [seizedPart, setSeizedPart] = useState<SeizedPart | null>(null);
  const [seizureType, setSeizureType] = useState<SeizureType | null>(null);
  const [reason, setReason] = useState<string | null>(null);
  const [quantity, setQuantity] = useState("1");
  const [unit, setUnit] = useState<Unit | null>("pieces");
  const [notes, setNotes] = useState("");
  const [photos, setPhotos] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const validate = () => {
    const newErrors: Record<string, string> = {};
    if (!species) newErrors.species = "Espèce obligatoire";
    if (!seizedPart) newErrors.seized_part = "Partie saisie obligatoire";
    if (!seizureType) newErrors.seizure_type = "Type de saisie obligatoire";
    if (!reason) newErrors.reason = "Motif obligatoire";
    const qty = Number(quantity);
    if (!quantity || Number.isNaN(qty) || qty <= 0) {
      newErrors.quantity = "Quantité doit être > 0";
    }
    if (!unit) newErrors.unit = "Unité obligatoire";

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handlePickImage = async () => {
    if (photos.length >= MAX_PHOTOS) {
      Alert.alert("Limite atteinte", "Maximum 3 photos par saisie");
      return;
    }

    const { status } = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (status !== "granted") {
      Alert.alert(
        "Permission refusée",
        "L'accès aux photos est nécessaire pour ajouter des images."
      );
      return;
    }

    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      quality: 0.5,
      allowsEditing: true,
      base64: true,
    });

    if (!result.canceled && result.assets && result.assets.length > 0) {
      const asset = result.assets[0];
      if (asset.base64) {
        const base64 = `data:${asset.type || "image/jpeg"};base64,${asset.base64}`;
        setPhotos((prev) => [...prev, base64]);
      }
    }
  };

  const handleSubmit = async () => {
    if (!validate()) return;

    setLoading(true);
    try {
      await createSeizure({
        species: species!,
        seized_part: seizedPart!,
        seizure_type: seizureType!,
        reason: reason!,
        quantity: Number(quantity),
        unit: unit!,
        notes: notes.trim() || undefined,
        photos,
      });

      Alert.alert("Succès", "Saisie enregistrée", [
        {
          text: "OK",
          onPress: () => {
            // reset formulaire
            setSpecies(null);
            setSeizedPart(null);
            setSeizureType(null);
            setReason(null);
            setQuantity("1");
            setUnit("pieces");
            setNotes("");
            setPhotos([]);
            router.replace("/inspector");
          },
        },
      ]);
    } catch (e) {
      Alert.alert(
        "Erreur",
        "Erreur lors de l'enregistrement de la saisie. Vérifiez votre connexion."
      );
    } finally {
      setLoading(false);
    }
  };

  const renderChipRow = <T extends string>(
    options: { label: string; value: T }[],
    selected: T | null,
    onSelect: (value: T) => void
  ) => (
    <View style={styles.chipRow}>
      {options.map((opt) => {
        const isSelected = selected === opt.value;
        return (
          <TouchableOpacity
            key={opt.value}
            style={[styles.chip, isSelected && styles.chipSelected]}
            onPress={() => onSelect(opt.value)}
          >
            <Text style={[styles.chipText, isSelected && styles.chipTextSelected]}>
              {opt.label}
            </Text>
          </TouchableOpacity>
        );
      })}
    </View>
  );

  return (
    <KeyboardAvoidingView
      style={{ flex: 1 }}
      behavior={Platform.OS === "ios" ? "padding" : "height"}
    >
      <ScrollView contentContainerStyle={styles.container}>
        <Text style={styles.title}>Nouvelle saisie</Text>

        <Text style={styles.label}>Espèce *</Text>
        {renderChipRow(SPECIES_OPTIONS, species, setSpecies)}
        {errors.species && <Text style={styles.error}>{errors.species}</Text>}

        <Text style={styles.label}>Partie saisie *</Text>
        {renderChipRow(PART_OPTIONS, seizedPart, setSeizedPart)}
        {errors.seized_part && (
          <Text style={styles.error}>{errors.seized_part}</Text>
        )}

        <Text style={styles.label}>Type de saisie *</Text>
        {renderChipRow(SEIZURE_TYPE_OPTIONS, seizureType, setSeizureType)}
        {errors.seizure_type && (
          <Text style={styles.error}>{errors.seizure_type}</Text>
        )}

        <Text style={styles.label}>Motif *</Text>
        <View style={styles.chipRow}>
          {REASON_OPTIONS.map((r) => {
            const selected = reason === r;
            return (
              <TouchableOpacity
                key={r}
                style={[styles.chip, selected && styles.chipSelected]}
                onPress={() => setReason(r)}
              >
                <Text
                  style={[styles.chipText, selected && styles.chipTextSelected]}
                >
                  {r}
                </Text>
              </TouchableOpacity>
            );
          })}
        </View>
        {errors.reason && <Text style={styles.error}>{errors.reason}</Text>}

        <Text style={styles.label}>Quantité *</Text>
        <View style={styles.row}>
          <TextInput
            style={[styles.input, { flex: 1 }]}
            value={quantity}
            onChangeText={setQuantity}
            keyboardType="numeric"
          />
          <View style={{ width: 12 }} />
          <View style={{ flex: 1 }}>
            <Text style={styles.labelSmall}>Unité *</Text>
            {renderChipRow(UNIT_OPTIONS, unit, (value) => setUnit(value))}
          </View>
        </View>
        {errors.quantity && <Text style={styles.error}>{errors.quantity}</Text>}
        {errors.unit && <Text style={styles.error}>{errors.unit}</Text>}

        <Text style={styles.label}>Notes (optionnel)</Text>
        <TextInput
          style={[styles.input, { height: 80, textAlignVertical: "top" }]}
          value={notes}
          onChangeText={setNotes}
          multiline
          placeholder="Notes complémentaires"
        />

        <Text style={styles.label}>Photos (max {MAX_PHOTOS})</Text>
        <View style={styles.row}>
          <TouchableOpacity
            style={styles.secondaryButton}
            onPress={handlePickImage}
          >
            <Text style={styles.secondaryButtonText}>Ajouter une photo</Text>
          </TouchableOpacity>
          <Text style={styles.photoCount}>{photos.length} / {MAX_PHOTOS}</Text>
        </View>

        <TouchableOpacity
          style={styles.primaryButton}
          onPress={handleSubmit}
          disabled={loading}
        >
          {loading ? (
            <ActivityIndicator color="#FFF" />
          ) : (
            <Text style={styles.primaryButtonText}>Enregistrer</Text>
          )}
        </TouchableOpacity>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    paddingHorizontal: 16,
    paddingTop: 16,
    paddingBottom: 32,
    backgroundColor: "#FFFFFF",
  },
  title: {
    fontSize: 22,
    fontWeight: "700",
    color: "#C62828",
    marginBottom: 16,
  },
  label: {
    fontSize: 14,
    color: "#333",
    marginBottom: 4,
    marginTop: 12,
  },
  labelSmall: {
    fontSize: 12,
    color: "#555",
    marginBottom: 4,
  },
  input: {
    borderWidth: 1,
    borderColor: "#DDD",
    borderRadius: 8,
    paddingHorizontal: 10,
    paddingVertical: 8,
    fontSize: 14,
    backgroundColor: "#FFF",
  },
  error: {
    color: "#C62828",
    marginTop: 4,
  },
  chipRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 8,
  },
  chip: {
    borderRadius: 16,
    borderWidth: 1,
    borderColor: "#C62828",
    paddingHorizontal: 12,
    paddingVertical: 6,
    marginRight: 4,
    marginBottom: 4,
  },
  chipSelected: {
    backgroundColor: "#C62828",
  },
  chipText: {
    color: "#C62828",
    fontSize: 13,
  },
  chipTextSelected: {
    color: "#FFF",
  },
  row: {
    flexDirection: "row",
    alignItems: "center",
    marginTop: 4,
  },
  secondaryButton: {
    borderRadius: 8,
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderWidth: 1,
    borderColor: "#C62828",
  },
  secondaryButtonText: {
    color: "#C62828",
    fontWeight: "500",
  },
  photoCount: {
    marginLeft: 12,
    fontSize: 14,
    color: "#555",
  },
  primaryButton: {
    marginTop: 24,
    backgroundColor: "#C62828",
    borderRadius: 8,
    paddingVertical: 14,
    alignItems: "center",
  },
  primaryButtonText: {
    color: "#FFF",
    fontSize: 16,
    fontWeight: "600",
  },
});
