import React, { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { FileText, Clock, CheckCircle2, AlertCircle, RefreshCw } from "lucide-react";
import axios from "axios";
import { toast } from "sonner";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const PrescriptionList = ({ refreshTrigger }) => {
  const [prescriptions, setPrescriptions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [editValues, setEditValues] = useState({});

  const fetchPrescriptions = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API}/prescriptions`);
      setPrescriptions(response.data);
      setError(null);
    } catch (err) {
      console.error("Error fetching prescriptions:", err);
      setError("Failed to load prescriptions");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPrescriptions();
  }, [refreshTrigger]);

  // Poll for updates every 3 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      fetchPrescriptions();
    }, 3000);

    return () => clearInterval(interval);
  }, []);

  const getStatusBadge = (status) => {
    switch (status) {
      case "completed":
        return (
          <Badge className="bg-green-100 text-green-800 hover:bg-green-100" data-testid="status-completed">
            <CheckCircle2 className="h-3 w-3 mr-1" />
            Completed
          </Badge>
        );
      case "processing":
        return (
          <Badge className="bg-blue-100 text-blue-800 hover:bg-blue-100" data-testid="status-processing">
            <RefreshCw className="h-3 w-3 mr-1 animate-spin" />
            Processing
          </Badge>
        );
      case "pending":
        return (
          <Badge className="bg-yellow-100 text-yellow-800 hover:bg-yellow-100" data-testid="status-pending">
            <Clock className="h-3 w-3 mr-1" />
            Pending
          </Badge>
        );
      case "failed":
        return (
          <Badge className="bg-red-100 text-red-800 hover:bg-red-100" data-testid="status-failed">
            <AlertCircle className="h-3 w-3 mr-1" />
            Failed
          </Badge>
        );
      default:
        return <Badge>{status}</Badge>;
    }
  };

  if (loading && prescriptions.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5" />
            Processed Prescriptions
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-32" />
          ))}
        </CardContent>
      </Card>
    );
  }

  return (
    <Card data-testid="prescription-list">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <FileText className="h-5 w-5" />
          Processed Prescriptions
        </CardTitle>
      </CardHeader>
      <CardContent>
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700 mb-4">
            {error}
          </div>
        )}

        {prescriptions.length === 0 ? (
          <div className="text-center py-12">
            <FileText className="h-12 w-12 text-slate-300 mx-auto mb-4" />
            <p className="text-slate-500">No prescriptions uploaded yet</p>
          </div>
        ) : (
          <div className="space-y-4 max-h-[600px] overflow-y-auto">
            {prescriptions.map((prescription) => (
              <Card key={prescription.id} className="border" data-testid={`prescription-${prescription.id}`}>
                <CardContent className="p-4">
                  {/* Header */}
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <h3 className="font-medium text-slate-900" data-testid="prescription-filename">
                        {prescription.filename}
                      </h3>
                      <p className="text-xs text-slate-500 mt-1">
                        {new Date(prescription.upload_timestamp).toLocaleString()}
                      </p>
                    </div>
                    {getStatusBadge(prescription.processing_status)}
                  </div>

                  {/* Verification Form when awaiting human approval */}
                  {prescription.processing_status === "awaiting_verification" && prescription.suggested_data && (
                    <div className="bg-slate-50 rounded-lg p-4 space-y-3" data-testid="verification-form">
                      <h4 className="font-medium text-sm text-slate-700 mb-2">Verify Extracted Information</h4>
                      <div className="grid grid-cols-1 gap-2 text-sm">
                        {[
                          ["patient_name", "Patient"],
                          ["doctor_name", "Doctor"],
                          ["symptoms", "Symptoms"],
                          ["prescription", "Prescription"],
                          ["dosage", "Dosage"],
                          ["doctor_notes", "Notes"]
                        ].map(([key, label]) => {
                          const initial = prescription.suggested_data?.[key] || "";
                          const current = (editValues[prescription.id] && editValues[prescription.id][key]) ?? initial;
                          return (
                            <div key={key} className="space-y-1">
                              <Label className="text-xs">{label}</Label>
                              <Input
                                value={current}
                                onChange={(e) => setEditValues((prev) => ({
                                  ...prev,
                                  [prescription.id]: {
                                    ...(prev[prescription.id] || {}),
                                    [key]: e.target.value,
                                  }
                                }))}
                                className="text-sm"
                              />
                            </div>
                          );
                        })}

                        <div className="flex gap-2 mt-2">
                          <Button
                            onClick={async () => {
                              const body = {
                                ...prescription.suggested_data,
                                ...(editValues[prescription.id] || {}),
                              };
                              try {
                                await axios.post(`${API}/prescriptions/${prescription.id}/verify`, body);
                                toast.success("Prescription verified and saved");
                                fetchPrescriptions();
                              } catch (err) {
                                console.error("Verify error:", err);
                                toast.error(err.response?.data?.detail || "Verification failed");
                              }
                            }}
                          >
                            Approve & Save
                          </Button>
                          <Button
                            variant="secondary"
                            onClick={() => {
                              setEditValues((prev) => ({ ...prev, [prescription.id]: {} }));
                            }}
                          >
                            Reset
                          </Button>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Structured Data (verified) */}
                  {prescription.processing_status === "verified" &&
                    prescription.structured_data && (
                      <div className="bg-slate-50 rounded-lg p-4 space-y-2" data-testid="structured-data">
                        <h4 className="font-medium text-sm text-slate-700 mb-2">
                          Verified Information:
                        </h4>
                        <div className="grid grid-cols-1 gap-2 text-sm">
                          {prescription.structured_data.patient_name && (
                            <div>
                              <span className="text-slate-600">Patient:</span>{" "}
                              <span className="text-slate-900 font-medium" data-testid="patient-name">
                                {prescription.structured_data.patient_name}
                              </span>
                            </div>
                          )}
                          {prescription.structured_data.doctor_name && (
                            <div>
                              <span className="text-slate-600">Doctor:</span>{" "}
                              <span className="text-slate-900 font-medium" data-testid="doctor-name">
                                {prescription.structured_data.doctor_name}
                              </span>
                            </div>
                          )}
                          {prescription.structured_data.symptoms && (
                            <div>
                              <span className="text-slate-600">Symptoms:</span>{" "}
                              <span className="text-slate-900" data-testid="symptoms">
                                {prescription.structured_data.symptoms}
                              </span>
                            </div>
                          )}
                          {prescription.structured_data.prescription && (
                            <div>
                              <span className="text-slate-600">Prescription:</span>{" "}
                              <span className="text-slate-900 font-medium" data-testid="prescription">
                                {prescription.structured_data.prescription}
                              </span>
                            </div>
                          )}
                          {prescription.structured_data.dosage && (
                            <div>
                              <span className="text-slate-600">Dosage:</span>{" "}
                              <span className="text-slate-900" data-testid="dosage">
                                {prescription.structured_data.dosage}
                              </span>
                            </div>
                          )}
                          {prescription.structured_data.doctor_notes && (
                            <div>
                              <span className="text-slate-600">Notes:</span>{" "}
                              <span className="text-slate-900" data-testid="doctor-notes">
                                {prescription.structured_data.doctor_notes}
                              </span>
                            </div>
                          )}
                        </div>
                      </div>
                    )}

                  {/* Raw Text (if available but no structured data) */}
                  {prescription.processing_status === "completed" &&
                    prescription.raw_text &&
                    !prescription.structured_data && (
                      <div className="bg-slate-50 rounded-lg p-3 mt-3">
                        <h4 className="font-medium text-sm text-slate-700 mb-2">
                          Raw Text:
                        </h4>
                        <p className="text-sm text-slate-600 whitespace-pre-wrap" data-testid="raw-text">
                          {prescription.raw_text}
                        </p>
                      </div>
                    )}

                  {/* Error Message */}
                  {prescription.processing_status === "failed" &&
                    prescription.error_message && (
                      <div className="bg-red-50 border border-red-200 rounded-lg p-3 mt-3 text-sm text-red-700" data-testid="error-message">
                        Error: {prescription.error_message}
                      </div>
                    )}

                  {/* Processing/Pending Message */}
                  {["processing", "pending"].includes(
                    prescription.processing_status
                  ) && (
                    <p className="text-sm text-slate-500 mt-3">
                      Processing your prescription...
                    </p>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default PrescriptionList;
