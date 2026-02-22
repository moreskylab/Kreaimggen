{{/*
Expand the name of the chart.
*/}}
{{- define "kreaimggen.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "kreaimggen.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "kreaimggen.labels" -}}
helm.sh/chart: {{ include "kreaimggen.name" . }}-{{ .Chart.Version }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Selector labels for a given component
*/}}
{{- define "kreaimggen.selectorLabels" -}}
app.kubernetes.io/name: {{ include "kreaimggen.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/component: {{ .component }}
{{- end }}

{{/*
Service account name
*/}}
{{- define "kreaimggen.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "kreaimggen.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Database env block (backend and worker)
*/}}
{{- define "kreaimggen.dbEnv" -}}
- name: DATABASE_URL
  value: "postgresql+asyncpg://$(POSTGRES_USER):$(POSTGRES_PASSWORD)@{{ include "kreaimggen.fullname" . }}-postgres:5432/{{ .Values.postgres.database }}"
- name: DATABASE_SYNC_URL
  value: "postgresql+psycopg2://$(POSTGRES_USER):$(POSTGRES_PASSWORD)@{{ include "kreaimggen.fullname" . }}-postgres:5432/{{ .Values.postgres.database }}"
- name: POSTGRES_USER
  valueFrom:
    secretKeyRef:
      name: {{ include "kreaimggen.fullname" . }}-postgres-secret
      key: postgres-user
- name: POSTGRES_PASSWORD
  valueFrom:
    secretKeyRef:
      name: {{ include "kreaimggen.fullname" . }}-postgres-secret
      key: postgres-password
{{- end }}

{{/*
Image helper – prepend global registry if set
*/}}
{{- define "kreaimggen.image" -}}
{{- $reg := .Values.global.imageRegistry | default "" -}}
{{- if $reg -}}
{{ printf "%s/%s:%s" (trimSuffix "/" $reg) .image.repository .image.tag }}
{{- else -}}
{{ printf "%s:%s" .image.repository .image.tag }}
{{- end }}
{{- end }}

{{/*
Broker + backend env block (shared across backend, worker, flower)
*/}}
{{- define "kreaimggen.brokerEnv" -}}
- name: CELERY_BROKER_URL
  value: "amqp://$(RABBITMQ_USER):$(RABBITMQ_PASS)@{{ include "kreaimggen.fullname" . }}-rabbitmq:5672//"
- name: CELERY_RESULT_BACKEND
  value: "redis://{{ include "kreaimggen.fullname" . }}-redis:6379/0"
- name: REDIS_URL
  value: "redis://{{ include "kreaimggen.fullname" . }}-redis:6379/1"
- name: RABBITMQ_USER
  valueFrom:
    secretKeyRef:
      name: {{ include "kreaimggen.fullname" . }}-broker-secret
      key: rabbitmq-username
- name: RABBITMQ_PASS
  valueFrom:
    secretKeyRef:
      name: {{ include "kreaimggen.fullname" . }}-broker-secret
      key: rabbitmq-password
{{- end }}
