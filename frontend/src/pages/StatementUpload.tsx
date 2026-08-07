import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiService } from '../services/apiService';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { Table, TableRow, TableCell } from '../components/ui/Table';
import { useToast } from '../contexts/ToastContext';
import {
  UploadCloud,
  FileSpreadsheet,
  AlertTriangle,
  ArrowRight,
  RefreshCw,
  Info
} from 'lucide-react';
import type { StatementUploadPreview, Account } from '../types';

export const StatementUpload: React.FC = () => {
  const queryClient = useQueryClient();
  const toast = useToast();

  const [selectedAccount, setSelectedAccount] = useState<number>(0);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const [step, setStep] = useState<1 | 2>(1); // 1: Upload, 2: Preview & Import
  const [previewData, setPreviewData] = useState<StatementUploadPreview | null>(null);

  // Query Accounts for selection dropdown
  const { data: accounts = [], isLoading: loadingAccounts } = useQuery<Account[]>({
    queryKey: ['accounts'],
    queryFn: apiService.getAccounts,
  });

  React.useEffect(() => {
    if (accounts.length > 0 && selectedAccount === 0) {
      setSelectedAccount(accounts[0].id);
    }
  }, [accounts, selectedAccount]);

  // Mutator for statement upload (Step 1 -> Step 2)
  const uploadMutation = useMutation({
    mutationFn: ({ accountId, file }: { accountId: number; file: File }) =>
      apiService.uploadStatement(accountId, file),
    onSuccess: (data: StatementUploadPreview) => {
      setPreviewData(data);
      setStep(2);
      toast.showToast('Statement parsed successfully. Review preview below.', 'success');
    },
    onError: (err: any) => {
      toast.showToast(err.message || 'Failed to upload and parse statement.', 'error');
    },
  });

  // Mutator for statement finalize import (Step 2 -> Complete)
  const importMutation = useMutation({
    mutationFn: apiService.importStatement,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['transactions'] });
      queryClient.invalidateQueries({ queryKey: ['accounts'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      toast.showToast(
        `Import completed! Added ${data.imported_transactions} items. Skipped ${data.skipped_duplicates} duplicate records.`,
        'success'
      );
      // Reset
      handleReset();
    },
    onError: (err: any) => {
      toast.showToast(err.message || 'Failed to finalize statement import.', 'error');
    },
  });

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      const ext = file.name.split('.').pop()?.toLowerCase();
      if (ext === 'csv' || ext === 'xlsx' || ext === 'xls') {
        setSelectedFile(file);
      } else {
        toast.showToast('Invalid file format. Please upload CSV or Excel.', 'info');
      }
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
    }
  };

  const handleUploadSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (selectedAccount === 0) {
      toast.showToast('Please select a target account.', 'info');
      return;
    }
    if (!selectedFile) {
      toast.showToast('Please choose a statement file to upload.', 'info');
      return;
    }

    uploadMutation.mutate({
      accountId: selectedAccount,
      file: selectedFile,
    });
  };

  const handleImportSubmit = () => {
    if (!previewData) return;
    importMutation.mutate(previewData.statement_id);
  };

  const handleReset = () => {
    setSelectedFile(null);
    setPreviewData(null);
    setStep(1);
  };

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div>
        <h2 className="text-xl md:text-2xl font-extrabold text-slate-850 dark:text-slate-100 tracking-tight">
          Statement Import Gateway
        </h2>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
          Upload CSV/XLSX bank sheets, run duplicate filters, and integrate records.
          All monetary balances will automatically reconcile.
        </p>
      </div>

      {step === 1 ? (
        <Card className="max-w-2xl mx-auto w-full mt-4">
          <CardHeader>
            <CardTitle>Select Account & Choose File</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleUploadSubmit} className="flex flex-col gap-5">
              {/* Account Dropdown */}
              <div className="flex flex-col gap-1.5 text-left">
                <label className="text-xs font-semibold text-slate-655 dark:text-slate-400">
                  Target Destination Account
                </label>
                <select
                  value={selectedAccount}
                  onChange={(e) => setSelectedAccount(Number(e.target.value))}
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-350 dark:border-slate-800 bg-white/50 dark:bg-slate-900/50 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
                  disabled={loadingAccounts}
                  required
                >
                  {accounts.length === 0 ? (
                    <option value="0">-- No accounts available. Create one first --</option>
                  ) : (
                    accounts.map((a) => (
                      <option key={a.id} value={a.id}>
                        {a.name} (Current: ₹{a.balance})
                      </option>
                    ))
                  )}
                </select>
              </div>

              {/* Drag and Drop Zone */}
              <div className="flex flex-col gap-1 text-left">
                <span className="text-xs font-semibold text-slate-655 dark:text-slate-400">
                  Statement Sheet File (.csv, .xlsx, .xls)
                </span>
                <div
                  onDragEnter={handleDrag}
                  onDragOver={handleDrag}
                  onDragLeave={handleDrag}
                  onDrop={handleDrop}
                  className={`border-2 border-dashed rounded-2xl p-8 flex flex-col items-center justify-center transition-all ${
                    dragActive
                      ? 'border-indigo-650 bg-indigo-50/10'
                      : 'border-slate-300 dark:border-slate-800 bg-white/10 dark:bg-slate-900/5'
                  }`}
                >
                  <input
                    type="file"
                    id="file-upload"
                    accept=".csv,.xlsx,.xls"
                    onChange={handleFileChange}
                    className="hidden"
                  />
                  {selectedFile ? (
                    <div className="flex flex-col items-center gap-2 text-center">
                      <FileSpreadsheet className="w-12 h-12 text-indigo-500" />
                      <span className="text-sm font-bold text-slate-800 dark:text-slate-200">
                        {selectedFile.name}
                      </span>
                      <span className="text-[10px] text-slate-400">
                        {Math.round(selectedFile.size / 1024)} KB
                      </span>
                      <button
                        type="button"
                        onClick={() => setSelectedFile(null)}
                        className="text-xs font-bold text-rose-500 hover:underline mt-2"
                      >
                        Remove file
                      </button>
                    </div>
                  ) : (
                    <label
                      htmlFor="file-upload"
                      className="flex flex-col items-center gap-2 text-center cursor-pointer"
                    >
                      <UploadCloud className="w-12 h-12 text-slate-400 hover:text-indigo-650 transition-colors" />
                      <span className="text-sm font-bold text-slate-700 dark:text-slate-300">
                        Drag and drop statement file here
                      </span>
                      <span className="text-xs text-indigo-650 dark:text-indigo-400 font-semibold hover:underline">
                        or browse files
                      </span>
                      <span className="text-[10px] text-slate-400 mt-1">
                        Supports standard bank statement layout formats
                      </span>
                    </label>
                  )}
                </div>
              </div>

              {/* Submit */}
              <Button
                type="submit"
                isLoading={uploadMutation.isPending}
                disabled={!selectedFile || selectedAccount === 0}
                className="w-full mt-2"
              >
                Upload and Parse Preview
              </Button>
            </form>
          </CardContent>
        </Card>
      ) : (
        /* PREVIEW STEP */
        <div className="flex flex-col gap-6">
          {/* Back button */}
          <div className="flex justify-start">
            <Button onClick={handleReset} variant="outline" size="sm" leftIcon={<RefreshCw className="w-4 h-4" />}>
              Start Over
            </Button>
          </div>

          {previewData && (
            <>
              {/* Summary Metrics cards */}
              <div className="grid grid-cols-1 sm:grid-cols-4 gap-5">
                <Card>
                  <CardContent className="flex flex-col text-left">
                    <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                      Parsed Rows
                    </span>
                    <span className="text-2xl font-black text-slate-805 dark:text-slate-100 mt-1">
                      {previewData.total_rows}
                    </span>
                  </CardContent>
                </Card>

                <Card>
                  <CardContent className="flex flex-col text-left">
                    <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                      Valid Rows
                    </span>
                    <span className="text-2xl font-black text-emerald-600 mt-1">
                      {previewData.valid_rows}
                    </span>
                  </CardContent>
                </Card>

                <Card>
                  <CardContent className="flex flex-col text-left">
                    <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                      Duplicates Filtered
                    </span>
                    <span className="text-2xl font-black text-amber-500 mt-1">
                      {previewData.duplicate_rows}
                    </span>
                    <span className="text-[9px] text-slate-400 mt-1.5 font-medium">
                      Already in database (Will be skipped)
                    </span>
                  </CardContent>
                </Card>

                <Card>
                  <CardContent className="flex flex-col text-left">
                    <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                      Formatting Errors
                    </span>
                    <span className={`text-2xl font-black mt-1 ${previewData.invalid_rows > 0 ? 'text-rose-500' : 'text-slate-400'}`}>
                      {previewData.invalid_rows}
                    </span>
                  </CardContent>
                </Card>
              </div>

              {/* Warnings Panel */}
              {previewData.warnings.length > 0 && (
                <Card className="border border-amber-200 bg-amber-50/10 text-amber-700 dark:border-amber-950/40 dark:text-amber-300">
                  <CardContent className="p-4 flex items-start gap-3 text-left">
                    <AlertTriangle className="w-5 h-5 text-amber-500 shrink-0 mt-0.5" />
                    <div className="flex flex-col gap-1 text-xs">
                      <span className="font-bold">File Parser Warnings:</span>
                      <ul className="list-disc pl-4 mt-0.5 flex flex-col gap-0.5">
                        {previewData.warnings.map((warning, idx) => (
                          <li key={idx} className="font-semibold">{warning}</li>
                        ))}
                      </ul>
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Transactions Preview Table */}
              <Card>
                <CardHeader className="flex flex-row items-center justify-between">
                  <CardTitle>Sheet Transaction Preview</CardTitle>
                  <Button
                    onClick={handleImportSubmit}
                    isLoading={importMutation.isPending}
                    disabled={previewData.valid_rows === 0}
                    className="shadow-lg"
                    rightIcon={<ArrowRight className="w-4 h-4" />}
                  >
                    Finalize Import
                  </Button>
                </CardHeader>
                <CardContent>
                  <div className="flex items-center gap-2 mb-4 p-3 bg-indigo-50/20 dark:bg-indigo-950/10 rounded-xl text-xs text-slate-655 dark:text-slate-400 font-semibold text-left border border-indigo-150/30">
                    <Info className="w-4.5 h-4.5 text-indigo-600 shrink-0" />
                    <span>
                      Amber highlighted rows indicate duplicate records that will be automatically ignored to avoid double-charging your logs.
                    </span>
                  </div>

                  <Table headers={['Row', 'Date', 'Title / Description', 'Category', 'Type', 'Amount', 'Status']}>
                    {previewData.preview_transactions.map((tx, idx) => {
                      const isDuplicate = tx.duplicate;
                      const isValid = tx.valid;

                      let rowClass = '';
                      if (isDuplicate) rowClass = 'bg-amber-50/10 hover:bg-amber-100/10 border-l-4 border-l-amber-500';
                      if (!isValid) rowClass = 'bg-rose-50/10 hover:bg-rose-100/10 border-l-4 border-l-rose-500';

                      return (
                        <TableRow key={idx} className={rowClass}>
                          <TableCell className="text-slate-400 font-bold text-xs">{tx.row_number}</TableCell>
                          <TableCell className="whitespace-nowrap font-medium text-slate-500">{tx.date || '-'}</TableCell>
                          <TableCell className="max-w-[220px]">
                            <div className="flex flex-col text-left">
                              <span className="font-bold text-slate-805 dark:text-slate-205 truncate">{tx.merchant || tx.description || 'Unlabeled'}</span>
                              {tx.description && <span className="text-[10px] text-slate-400 truncate">{tx.description}</span>}
                            </div>
                          </TableCell>
                          <TableCell className="font-semibold text-slate-600 dark:text-slate-350">{tx.category || 'Uncategorized'}</TableCell>
                          <TableCell>
                            {tx.transaction_type && (
                              <Badge variant={tx.transaction_type === 'income' ? 'success' : 'danger'} className="uppercase text-[9px]">
                                {tx.transaction_type}
                              </Badge>
                            )}
                          </TableCell>
                          <TableCell className="font-black text-slate-805 dark:text-slate-50 whitespace-nowrap text-right">
                            {tx.amount ? `₹${tx.amount}` : '-'}
                          </TableCell>
                          <TableCell>
                            {!isValid ? (
                              <Badge variant="danger" className="text-[8px] tracking-wide" title={tx.error || 'Parsing error'}>
                                Error
                              </Badge>
                            ) : isDuplicate ? (
                              <Badge variant="warning" className="text-[8px] tracking-wide">
                                Duplicate
                              </Badge>
                            ) : (
                              <Badge variant="success" className="text-[8px] tracking-wide">
                                Ready
                              </Badge>
                            )}
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </Table>
                </CardContent>
              </Card>
            </>
          )}
        </div>
      )}
    </div>
  );
};
export default StatementUpload;
