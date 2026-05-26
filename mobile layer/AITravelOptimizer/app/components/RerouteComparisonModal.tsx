import React from 'react';
import { Modal, View, Text, Pressable, StyleSheet } from 'react-native';
import { colors } from '@/theme/colors';
import { typography } from '@/theme/typography';
import { TravelItineraryDay } from '@/navigators/navigationTypes';

interface RerouteComparisonModalProps {
  visible: boolean;
  oldDay: TravelItineraryDay | undefined;
  newDay: TravelItineraryDay | undefined;
  onConfirm: () => void;
  onCancel: () => void;
}

export const RerouteComparisonModal: React.FC<RerouteComparisonModalProps> = ({ 
  visible, oldDay, newDay, onConfirm, onCancel 
}) => {
  if (!oldDay || !newDay) return null;

  const oldCost = oldDay.stops.reduce((sum, s) => sum + (s.entrance_fee || 0), 0);
  const newCost = newDay.stops.reduce((sum, s) => sum + (s.entrance_fee || 0), 0);

  return (
    <Modal visible={visible} animationType="slide" transparent>
      <View style={styles.modalOverlay}>
        <View style={styles.modalContent}>
          <Text style={styles.title}>So sánh lịch trình mới</Text>
          
          <View style={styles.comparisonContainer}>
            {/* CŨ */}
            <View style={styles.column}>
              <Text style={styles.colTitle}>Hiện tại</Text>
              <Text style={styles.stat}>{oldDay.stops.length} điểm</Text>
              <Text style={styles.stat}>{oldDay.total_distance_km.toFixed(1)} km</Text>
              <Text style={styles.stat}>{oldCost > 0 ? (oldCost / 1000).toFixed(0) + 'k₫' : 'Free'}</Text>
            </View>
            
            <View style={styles.vsDivider}><Text style={styles.vsText}>VS</Text></View>

            {/* MỚI */}
            <View style={styles.column}>
              <Text style={styles.colTitle}>Đề xuất (AI)</Text>
              <Text style={[styles.stat, {color: colors.tint, fontWeight: 'bold'}]}>{newDay.stops.length} điểm</Text>
              <Text style={[styles.stat, {color: colors.tint, fontWeight: 'bold'}]}>{newDay.total_distance_km.toFixed(1)} km</Text>
              <Text style={[styles.stat, {color: colors.tint, fontWeight: 'bold'}]}>{newCost > 0 ? (newCost / 1000).toFixed(0) + 'k₫' : 'Free'}</Text>
            </View>
          </View>

          <View style={styles.actions}>
            <Pressable style={styles.cancelBtn} onPress={onCancel}>
              <Text style={styles.cancelText}>Hủy bỏ</Text>
            </Pressable>
            <Pressable style={styles.confirmBtn} onPress={onConfirm}>
              <Text style={styles.confirmText}>Áp dụng ngay</Text>
            </Pressable>
          </View>
        </View>
      </View>
    </Modal>
  );
};

const styles = StyleSheet.create({
  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'center', alignItems: 'center' },
  modalContent: { backgroundColor: 'white', padding: 20, borderRadius: 16, width: '90%' },
  title: { fontSize: 20, fontFamily: typography.primary.bold, textAlign: 'center', marginBottom: 20 },
  comparisonContainer: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 25 },
  column: { flex: 1, alignItems: 'center', backgroundColor: '#f9f9f9', padding: 15, borderRadius: 10 },
  colTitle: { fontSize: 16, fontFamily: typography.primary.semiBold, marginBottom: 10 },
  stat: { fontSize: 14, fontFamily: typography.primary.medium, marginVertical: 4 },
  vsDivider: { paddingHorizontal: 10 },
  vsText: { color: '#999', fontWeight: 'bold' },
  actions: { flexDirection: 'row', justifyContent: 'space-between', gap: 15 },
  cancelBtn: { flex: 1, padding: 14, backgroundColor: '#eee', borderRadius: 8, alignItems: 'center' },
  cancelText: { color: '#333', fontFamily: typography.primary.semiBold },
  confirmBtn: { flex: 1, padding: 14, backgroundColor: colors.tint, borderRadius: 8, alignItems: 'center' },
  confirmText: { color: 'white', fontFamily: typography.primary.semiBold }
});
