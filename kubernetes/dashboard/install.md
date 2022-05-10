helm repo add kubernetes-dashboard https://kubernetes.github.io/dashboard/
helm repo update
helm install k8sdashboard --set=service.type=NodePort kubernetes-dashboard/kubernetes-dashboard -n kubernetes-dashboard