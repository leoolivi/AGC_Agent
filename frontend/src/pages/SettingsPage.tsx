import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { api } from "@/api/client";
import { SourcesSettings } from "@/components/settings/SourcesSettings";
import { OnboardingFlow } from "@/components/onboarding/OnboardingFlow";
import { useState } from "react";

export function SettingsPage() {
  const qc = useQueryClient();
  const [showOnboarding, setShowOnboarding] = useState(false);

  const { data: googleStatus } = useQuery<{ connected: boolean }>({
    queryKey: ["google-status"],
    queryFn: async () => (await api.get("/api/v1/oauth/google/status")).data,
  });

  const connectGoogle = useMutation({
    mutationFn: async () => {
      const res = await api.post<{ authorization_url: string }>("/api/v1/oauth/google/authorize");
      window.location.href = res.data.authorization_url;
    },
  });

  const disconnectGoogle = useMutation({
    mutationFn: async () => { await api.post("/api/v1/oauth/google/revoke"); },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["google-status"] }),
  });

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-semibold">Impostazioni</h2>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Google Suite</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium">Account Google</p>
              <p className="text-xs text-muted-foreground">Gmail, Drive, Calendar</p>
            </div>
            {googleStatus?.connected ? (
              <div className="flex items-center gap-2">
                <Badge className="bg-success/10 text-success">Collegato</Badge>
                <Button size="sm" variant="destructive" onClick={() => disconnectGoogle.mutate()} disabled={disconnectGoogle.isPending}>
                  Scollega
                </Button>
              </div>
            ) : (
              <Button size="sm" onClick={() => connectGoogle.mutate()} disabled={connectGoogle.isPending}>
                Collega Google
              </Button>
            )}
          </div>
          {googleStatus?.connected && (
            <div className="text-xs text-muted-foreground space-y-1">
              <p>✓ Gmail — lettura inbox e invio email</p>
              <p>✓ Drive — importazione documenti</p>
              <p>✓ Calendar — creazione eventi da scadenze</p>
            </div>
          )}
        </CardContent>
      </Card>

      <SourcesSettings />

      {showOnboarding ? (
        <OnboardingFlow onComplete={() => setShowOnboarding(false)} onSkip={() => setShowOnboarding(false)} />
      ) : (
        <Button variant="outline" size="sm" onClick={() => setShowOnboarding(true)}>
          Avvia onboarding guidato
        </Button>
      )}
    </div>
  );
}
