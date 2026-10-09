import React, { useState } from 'react';
import { Modal } from '../ui/Modal';
import { Button } from '../ui/Button';
import { useResetDemo, useResetDemoPreview } from '../../api/demo';
import { AlertTriangle, Loader2, RotateCcw, Trash2 } from 'lucide-react';

interface ResetDemoModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const ResetDemoModal: React.FC<ResetDemoModalProps> = ({ isOpen, onClose }) => {
  const [clearUserDatasets, setClearUserDatasets] = useState(false);
  const { data: preview, isLoading: previewLoading } = useResetDemoPreview(isOpen);
  const resetMutation = useResetDemo();

  const handleConfirm = () => {
    resetMutation.mutate(
      { clearUserDatasets },
      {
        onSuccess: () => {
          onClose();
        },
      }
    );
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Reset Demo & Fleet Data"
      description="Administrative control to restore seeded demo machines to baseline state"
      maxWidth="md"
      footer={
        <div className="flex items-center gap-2">
          <Button variant="secondary" size="xs" onClick={onClose} disabled={resetMutation.isPending}>
            Cancel
          </Button>
          <Button
            variant={clearUserDatasets ? 'danger' : 'primary'}
            size="xs"
            onClick={handleConfirm}
            disabled={resetMutation.isPending}
            icon={
              resetMutation.isPending ? (
                <Loader2 className="w-3 h-3 animate-spin" />
              ) : clearUserDatasets ? (
                <Trash2 className="w-3 h-3" />
              ) : (
                <RotateCcw className="w-3 h-3" />
              )
            }
          >
            {resetMutation.isPending
              ? 'Resetting…'
              : clearUserDatasets
              ? 'Purge & Reset All'
              : 'Reset Demo Fleet Only'}
          </Button>
        </div>
      }
    >
      <div className="space-y-4 text-xs font-mono">
        <div className="p-3 bg-[#0d121a] rounded border border-[#1e2636] space-y-1.5 text-slate-300">
          <div className="font-semibold text-white flex items-center gap-1.5">
            <RotateCcw className="w-3.5 h-3.5 text-blue-400" /> Standard Demo Reset
          </div>
          <p className="text-[11px] text-slate-400 font-sans leading-relaxed">
            Restores the 3 seeded NASA C-MAPSS FD001 demo units (Healthy, Warning, Critical) to their initial cutoff cycles,
            clearing replay observations and resetting predictions.
          </p>
        </div>

        {/* Separate option for user-uploaded datasets */}
        <div className="p-3 bg-[#131924] rounded border border-[#232f42] space-y-2">
          <label className="flex items-start gap-2.5 cursor-pointer">
            <input
              type="checkbox"
              checked={clearUserDatasets}
              onChange={(e) => setClearUserDatasets(e.target.checked)}
              className="mt-0.5 rounded border-rose-600 bg-rose-950 text-rose-500 focus:ring-rose-500"
            />
            <div>
              <span className="font-bold text-slate-200">
                Also delete user-uploaded datasets and machines
              </span>
              <p className="text-[11px] text-slate-400 font-sans mt-0.5">
                Permanently purges all uploaded telemetry files, created machine entities, scored predictions, and associated alerts.
              </p>
            </div>
          </label>

          {clearUserDatasets && (
            <div className="mt-2 pt-2 border-t border-[#1e2636] space-y-1.5 text-[11px]">
              {previewLoading ? (
                <div className="flex items-center gap-1 text-slate-400">
                  <Loader2 className="w-3 h-3 animate-spin" /> Scanning database for user data…
                </div>
              ) : preview ? (
                <div className="p-2 bg-rose-950/30 rounded border border-rose-900/50 text-rose-200 space-y-1">
                  <div className="font-bold text-rose-400 flex items-center gap-1">
                    <AlertTriangle className="w-3.5 h-3.5" /> Items to be deleted:
                  </div>
                  <ul className="list-disc list-inside space-y-0.5 text-slate-300">
                    <li>
                      <strong className="text-white">{preview.user_datasets_to_delete}</strong> dataset(s)
                      {preview.user_dataset_names.length > 0 && (
                        <span> ({preview.user_dataset_names.join(', ')})</span>
                      )}
                    </li>
                    <li>
                      <strong className="text-white">{preview.user_machines_to_delete}</strong> machine entity(ies)
                    </li>
                    <li>
                      <strong className="text-white">{preview.user_predictions_to_delete}</strong> prediction record(s)
                    </li>
                    <li>
                      <strong className="text-white">{preview.user_alerts_to_delete}</strong> open alert(s)
                    </li>
                  </ul>
                </div>
              ) : null}
            </div>
          )}
        </div>
      </div>
    </Modal>
  );
};
