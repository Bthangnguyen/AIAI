import React from 'react';
import { Modal, View, Text, Pressable, StyleSheet } from 'react-native';
import { colors } from '@/theme/colors';
import { typography } from '@/theme/typography';
import { ReRoutePayload } from '@/navigators/navigationTypes';

interface InfeasibleRerouteModalProps {
  visible: boolean;
  onClose: () => void;
  onSelectOption: (userState: ReRoutePayload['user_state']) => void;
}

const OPTIONS = [
  { id: '1', label: '1. Giảm bớt địa điểm', state: { wants_shorter_plan: true } },
  { id: '2', label: '2. Tăng thời gian chuyến đi', state: { extend_time: true } },
  { id: '3', label: '3. Ưu tiên điểm miễn phí', state: { prioritize_free: true } },
  { id: '4', label: '4. Tạo bản lịch nhẹ hơn', state: { tired: true, wants_shorter_plan: true } }
];

export const InfeasibleRerouteModal: React.FC<InfeasibleRerouteModalProps> = ({ visible, onClose, onSelectOption }) => {
  return (
    <Modal visible={visible} animationType="fade" transparent>
      <View style={styles.modalOverlay}>
        <View style={styles.modalContent}>
          <View style={styles.header}>
            <Text style={styles.title}>Lịch hiện tại quá dày</Text>
            <Pressable onPress={onClose}><Text style={styles.closeBtn}>✕</Text></Pressable>
          </View>
          
          <Text style={styles.subtitle}>
            Chúng tôi không thể xếp tất cả các điểm vào thời gian còn lại. Bạn muốn xử lý thế nào?
          </Text>

          <View style={styles.optionsContainer}>
            {OPTIONS.map(opt => (
              <Pressable 
                key={opt.id} 
                style={styles.optionBtn} 
                onPress={() => {
                  onClose();
                  onSelectOption(opt.state);
                }}
              >
                <Text style={styles.optionText}>{opt.label}</Text>
              </Pressable>
            ))}
          </View>
        </View>
      </View>
    </Modal>
  );
};

const styles = StyleSheet.create({
  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'center', padding: 20 },
  modalContent: { backgroundColor: 'white', padding: 20, borderRadius: 16 },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 },
  title: { fontSize: 18, fontFamily: typography.primary.bold, color: '#d32f2f' },
  subtitle: { fontSize: 14, color: '#333', marginBottom: 20, lineHeight: 20 },
  closeBtn: { fontSize: 20, padding: 5 },
  optionsContainer: { gap: 10 },
  optionBtn: { backgroundColor: '#f5f5f5', padding: 15, borderRadius: 8, borderWidth: 1, borderColor: '#eee' },
  optionText: { color: '#333', fontSize: 15, fontFamily: typography.primary.medium }
});
