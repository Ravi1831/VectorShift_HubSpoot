import { useState } from 'react';
import {
    Box,
    Button,
    Card,
    CardContent,
    Typography,
    Table,
    TableBody,
    TableCell,
    TableContainer,
    TableHead,
    TableRow,
    Paper,
} from '@mui/material';
import axios from 'axios';

// API endpoint mapping for different integrations
const endpointMapping = {
    'Notion': 'notion',
    'Airtable': 'airtable',
    'HubSpot': 'hubspot',
};

export const DataForm = ({ integrationType, credentials }) => {
    const [loadedData, setLoadedData] = useState(null);
    const endpoint = endpointMapping[integrationType];

    const handleLoad = async () => {
        try {
            const formData = new FormData();
            formData.append('credentials', JSON.stringify(credentials));
            const response = await axios.post(`http://localhost:8000/integrations/${endpoint}/load`, formData);
            const data = response.data;
            setLoadedData(data);
        } catch (error) {
            alert(error?.response?.data?.detail);
        }
    }


    return (
        <Box display='flex' justifyContent='center' alignItems='center' flexDirection='column' width='100%'>
            <Box display='flex' flexDirection='column' width='100%'>
                {loadedData && Array.isArray(loadedData) && loadedData.length > 0 && (
                    <Box sx={{ mt: 2, mb: 2 }}>
                        <Typography variant="h6" sx={{ mb: 2 }}>
                            Loaded {loadedData.length} items from {integrationType}
                        </Typography>
                        
                        <TableContainer component={Paper} sx={{ mb: 2 }}>
                            <Table>
                                <TableHead>
                                    <TableRow>
                                        <TableCell>ID</TableCell>
                                        <TableCell>Name</TableCell>
                                        <TableCell>Type</TableCell>
                                        <TableCell>Created</TableCell>
                                        <TableCell>Modified</TableCell>
                                    </TableRow>
                                </TableHead>
                                <TableBody>
                                    {loadedData.map((item, index) => (
                                        <TableRow key={item.id || index}>
                                            <TableCell>{item.id || 'N/A'}</TableCell>
                                            <TableCell>{item.name || 'N/A'}</TableCell>
                                            <TableCell>{item.type || 'N/A'}</TableCell>
                                            <TableCell>
                                                {item.creation_time ? new Date(item.creation_time).toLocaleDateString() : '-'}
                                            </TableCell>
                                            <TableCell>
                                                {item.last_modified_time ? new Date(item.last_modified_time).toLocaleDateString() : '-'}
                                            </TableCell>
                                        </TableRow>
                                    ))}
                                </TableBody>
                            </Table>
                        </TableContainer>
                    </Box>
                )}
                
                {loadedData && !Array.isArray(loadedData) && (
                    <Box sx={{ mt: 2, mb: 2 }}>
                        <Typography variant="h6" sx={{ mb: 2 }}>
                            Data from {integrationType}
                        </Typography>
                        <Card>
                            <CardContent>
                                <pre style={{ whiteSpace: 'pre-wrap', fontSize: '12px' }}>
                                    {JSON.stringify(loadedData, null, 2)}
                                </pre>
                            </CardContent>
                        </Card>
                    </Box>
                )}
                
                <Button
                    onClick={handleLoad}
                    sx={{mt: 2}}
                    variant='contained'
                >
                    Load Data
                </Button>
                <Button
                    onClick={() => setLoadedData(null)}
                    sx={{mt: 1}}
                    variant='contained'
                >
                    Clear Data
                </Button>
            </Box>
        </Box>
    );
}
