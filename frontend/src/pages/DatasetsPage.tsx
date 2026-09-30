import React from 'react';
import type { Dataset, Role } from '../types';
import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { UploadCloud, ArrowRight, Shield } from 'lucide-react';

interface DatasetsPageProps {
  datasets: Dataset[];
  currentUserRole: Role;
  onOpenUploadWizard: () => void;
  onViewSchemaMapping: (datasetId: string) => void;
}

export const DatasetsPage: React.FC<DatasetsPageProps> = ({
  datasets,
  currentUserRole,
  onOpenUploadWizard,
  onViewSchemaMapping,
}) => {
  return (
    <div className="space-y-5 animate-in fade-in duration-100 select-none">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-3 bg-[#111621] border border-[#1e2636] rounded-md">
        <div>
          <h1 className="text-sm font-bold text-white font-mono uppercase tracking-wide">
            Dataset Registry & Versions
          </h1>
          <p className="text-[11px] text-slate-400">
            Immutable datasets with SHA-256 integrity &bull; Schema validation &bull; Compatibility gate
          </p>
        </div>

        {currentUserRole === 'admin' ? (
          <Button
            variant="primary"
            size="xs"
            onClick={onOpenUploadWizard}
            icon={<UploadCloud className="w-3.5 h-3.5" />}
          >
            Upload New Dataset
          </Button>
        ) : (
          <div className="text-[11px] font-mono text-slate-500 flex items-center gap-1.5">
            <Shield className="w-3 h-3 text-slate-500" />
            <span>Upload restricted to Administrator</span>
          </div>
        )}
      </div>

      {/* Dataset Version Table */}
      <Card
        title="Registered Datasets & Schema Mappings"
        subtitle="Versioned ingestion records &bull; Incompatible uploads are blocked from inference (HTTP 409)"
      >
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse tabular-nums">
            <thead>
              <tr className="border-b border-[#20293a] bg-[#111721] text-[10px] font-mono font-semibold text-slate-400 uppercase tracking-wider">
                <th className="py-2.5 px-3">Dataset Name & Version</th>
                <th className="py-2.5 px-3">Adapter Key</th>
                <th className="py-2.5 px-3">Origin</th>
                <th className="py-2.5 px-3">Row Count</th>
                <th className="py-2.5 px-3">Unit Count</th>
                <th className="py-2.5 px-3">Status</th>
                <th className="py-2.5 px-3">SHA-256 Checksum</th>
                <th className="py-2.5 px-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#18212e]">
              {datasets.map((ds) => {
                const isRejected = ds.status === 'rejected_incompatible';

                return (
                  <tr key={ds.id} className="hover:bg-[#161d29] transition-colors">
                    <td className="py-2.5 px-3">
                      <div className="font-semibold text-slate-100">{ds.name}</div>
                      <div className="text-[10px] text-slate-400 font-mono">{ds.version}</div>
                    </td>
                    <td className="py-2.5 px-3 font-mono text-slate-300">{ds.adapterKey}</td>
                    <td className="py-2.5 px-3">
                      <Badge variant="demo" size="xs">
                        {ds.dataOrigin}
                      </Badge>
                    </td>
                    <td className="py-2.5 px-3 font-mono text-slate-300">
                      {ds.rowCount.toLocaleString()} rows
                    </td>
                    <td className="py-2.5 px-3 font-mono text-slate-300">
                      {ds.unitCount} units
                    </td>
                    <td className="py-2.5 px-3">
                      <span
                        className={`text-[10px] px-1.5 py-0.5 rounded font-mono font-bold uppercase tracking-wider ${
                          isRejected
                            ? 'bg-rose-950/70 text-rose-300 border border-rose-800'
                            : 'bg-emerald-950/70 text-emerald-300 border border-emerald-800'
                        }`}
                      >
                        {ds.status}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 font-mono text-[10px] text-slate-500">
                      {ds.checksumSha256.slice(0, 14)}...
                    </td>
                    <td className="py-2.5 px-3 text-right">
                      <Button
                        variant={isRejected ? 'danger' : 'secondary'}
                        size="xs"
                        onClick={() => onViewSchemaMapping(ds.id)}
                        icon={<ArrowRight className="w-3 h-3" />}
                      >
                        {isRejected ? 'Blocking Matrix' : 'View Mapping'}
                      </Button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
};
